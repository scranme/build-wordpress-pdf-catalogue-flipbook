#!/usr/bin/env python3
"""Build a self-contained WordPress plugin from a PDF or ordered page images."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
import shutil
import statistics
import sys
import tempfile
from urllib.parse import urlsplit
import zipfile

from PIL import Image, ImageOps, UnidentifiedImageError

from validate_wordpress_package import SLUG, ValidationError, validate_package


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}
TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "wordpress-plugin-template"


class BuildError(ValueError):
    """A source or build option is invalid."""


@dataclass
class BuildConfig:
    input: Path
    output: Path
    plugin_name: str = "WordPress PDF Catalogue Flipbook"
    plugin_slug: str = "wp-product-flipbook"
    catalogue_title: str = "Product Catalogue"
    catalogue_slug: str = "default"
    metadata: Path | None = None
    page_long_edge: int = 1600
    retina_long_edge: int = 2400
    thumb_long_edge: int = 320
    quality: int = 88
    background: str = "FFFFFF"
    include_pdf: bool = False
    no_pad_even: bool = False
    version: str = "1.0.1"


def natural_key(path: Path):
    return [int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", path.name)]


def valid_link_url(value: object) -> bool:
    if not isinstance(value, str) or not value or any(ord(char) < 32 for char in value) or "\\" in value:
        return False
    if value.startswith("/") and not value.startswith("//"):
        return True
    try:
        parsed = urlsplit(value)
        return parsed.scheme in {"https", "http"} and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:
        return False


def load_metadata(path: Path | None) -> dict:
    if path is None:
        return {"pages": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        raise BuildError(f"Cannot read metadata JSON: {error}") from error
    if not isinstance(data, dict) or not isinstance(data.get("pages", {}), dict):
        raise BuildError("Metadata must be an object with an optional pages object")
    if "description" in data and not isinstance(data["description"], str):
        raise BuildError("Metadata description must be text")
    for number, page in data.get("pages", {}).items():
        if not re.fullmatch(r"[1-9][0-9]*", number) or not isinstance(page, dict):
            raise BuildError("Metadata page keys must be one-based positive integers")
        for key in ("title", "alt", "searchText"):
            if key in page and not isinstance(page[key], str):
                raise BuildError(f"Page {number}: {key} must be text")
        links = page.get("links", [])
        if not isinstance(links, list):
            raise BuildError(f"Page {number}: links must be an array")
        for link in links:
            if not isinstance(link, dict) or not valid_link_url(link.get("url")):
                raise BuildError(f"Page {number}: hotspot needs a safe HTTP(S) or site-relative URL")
            if not isinstance(link.get("label"), str) or not link["label"].strip():
                raise BuildError(f"Page {number}: hotspot needs a descriptive label")
            for key in ("x", "y", "width", "height"):
                value = link.get(key)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise BuildError(f"Page {number}: hotspot {key} must be a finite number")
                if value < 0 or value > 100 or (key in {"width", "height"} and value == 0):
                    raise BuildError(f"Page {number}: hotspot {key} is outside the page")
            if link["x"] + link["width"] > 100 or link["y"] + link["height"] > 100:
                raise BuildError(f"Page {number}: hotspot extends outside the page")
    return data


class ImageSource:
    def __init__(self, directory: Path):
        self.files = sorted((p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES), key=natural_key)
        if not self.files:
            raise BuildError("The image folder contains no supported page images")
        self.dimensions = []
        for path in self.files:
            try:
                with Image.open(path) as image:
                    if getattr(image, "n_frames", 1) != 1:
                        raise BuildError(f"Multi-frame input is ambiguous; export individual pages first: {path.name}")
                    oriented = ImageOps.exif_transpose(image)
                    self.dimensions.append(oriented.size)
            except (OSError, UnidentifiedImageError) as error:
                raise BuildError(f"Cannot open image {path.name}: {error}") from error

    def read(self, index: int, long_edge: int):
        with Image.open(self.files[index]) as image:
            return ImageOps.exif_transpose(image).copy(), ""

    def close(self):
        pass


class PdfSource:
    def __init__(self, path: Path):
        try:
            import pypdfium2 as pdfium
        except ImportError as error:
            raise BuildError("PDF input requires pypdfium2. Run: python -m pip install -r requirements.txt") from error
        try:
            self.document = pdfium.PdfDocument(str(path))
            self.dimensions = []
            for index in range(len(self.document)):
                page = self.document[index]
                try:
                    self.dimensions.append(page.get_size())
                finally:
                    page.close()
            if not self.dimensions:
                raise BuildError("PDF contains no pages")
        except Exception as error:
            if hasattr(self, "document"):
                self.document.close()
            raise BuildError(f"Cannot read PDF: {error}") from error

    def read(self, index: int, long_edge: int):
        page = self.document[index]
        try:
            textpage = page.get_textpage()
            try:
                text = textpage.get_text_range()
            finally:
                textpage.close()
            scale = long_edge / max(page.get_size())
            bitmap = page.render(scale=scale)
            try:
                image = bitmap.to_pil().copy()
            finally:
                bitmap.close()
            return image, text.replace("\x00", "")
        except Exception as error:
            raise BuildError(f"Cannot render PDF page {index + 1}: {error}") from error
        finally:
            page.close()

    def close(self):
        self.document.close()


def dominant_ratio(dimensions: list[tuple[int, int]]) -> float:
    ratios = [width / height for width, height in dimensions]
    buckets = Counter(round(ratio, 3) for ratio in ratios)
    top = buckets.most_common(1)[0][1]
    winners = [ratio for ratio, count in buckets.items() if count == top]
    return float(statistics.median(winners))


def fit_canvas(image: Image.Image, ratio: float, long_edge: int, background: str) -> Image.Image:
    """Contain artwork without cropping, distortion, or raster upscaling."""
    edge = min(long_edge, max(image.size))
    width = max(1, round(edge if ratio >= 1 else edge * ratio))
    height = max(1, round(edge / ratio if ratio >= 1 else edge))
    image = image.convert("RGBA")
    image.thumbnail((width, height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (width, height), "#" + background)
    canvas.paste(image, ((width - image.width) // 2, (height - image.height) // 2), image)
    return canvas


def transform_hotspots(links: list[dict], source_size: tuple[int, int], canvas_size: tuple[int, int]) -> list[dict]:
    """Metadata coordinates describe source artwork; follow it into padded pages."""
    if not links:
        return []
    artwork = Image.new("L", source_size)
    artwork.thumbnail(canvas_size, Image.Resampling.NEAREST)
    width, height = artwork.size
    artwork.close()
    canvas_width, canvas_height = canvas_size
    left = (canvas_width - width) // 2
    top = (canvas_height - height) // 2
    result = []
    for original in links:
        link = {key: original[key] for key in ("url", "label")}
        link["x"] = round((left + original["x"] * width / 100) / canvas_width * 100, 6)
        link["y"] = round((top + original["y"] * height / 100) / canvas_height * 100, 6)
        link["width"] = round(original["width"] * width / canvas_width, 6)
        link["height"] = round(original["height"] * height / canvas_height, 6)
        result.append(link)
    return result


def save_variant(image: Image.Image, path: Path, edge: int, quality: int) -> tuple[int, int]:
    variant = image.copy()
    variant.thumbnail((edge, edge), Image.Resampling.LANCZOS)
    variant.save(path, "WEBP", quality=quality, method=4)
    return variant.size


def validate_config(config: BuildConfig):
    for name in ("plugin_slug", "catalogue_slug"):
        if not SLUG.fullmatch(getattr(config, name)) or len(getattr(config, name)) > 64:
            raise BuildError(f"{name.replace('_', '-')} must be a lowercase slug of at most 64 characters")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-.][a-zA-Z0-9.-]+)?", config.version):
        raise BuildError("version must be a semantic version such as 1.0.0")
    if not config.plugin_name.strip() or any(ch in config.plugin_name for ch in ("\r", "\n", "<?", "?>", "*/")):
        raise BuildError("plugin-name must be a nonempty single line without PHP delimiters")
    if not config.catalogue_title.strip():
        raise BuildError("catalogue-title cannot be empty")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", config.background):
        raise BuildError("background must be a six-digit RGB hex color")
    if not 1 <= config.quality <= 100:
        raise BuildError("quality must be between 1 and 100")
    if not 32 <= config.thumb_long_edge <= config.page_long_edge <= config.retina_long_edge <= 6000:
        raise BuildError("Require 32 <= thumb-long-edge <= page-long-edge <= retina-long-edge <= 6000")
    if config.include_pdf and (not config.input.is_file() or config.input.suffix.lower() != ".pdf"):
        raise BuildError("--include-pdf requires a PDF input")


def write_json(path: Path, value: object):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build(config: BuildConfig, template: Path = TEMPLATE) -> dict:
    config.input = config.input.resolve()
    config.output = config.output.resolve()
    validate_config(config)
    metadata = load_metadata(config.metadata)
    if config.input.is_dir():
        # Avoid rediscovering our own output on later runs.
        if config.output == config.input or config.input in config.output.parents:
            raise BuildError("Choose an output directory outside the source image folder")
        source = ImageSource(config.input)
        source_type = "images"
    elif config.input.is_file() and config.input.suffix.lower() == ".pdf":
        source = PdfSource(config.input)
        source_type = "pdf"
    else:
        raise BuildError("Input must be an existing PDF or an image directory")
    try:
        if not template.is_dir():
            raise BuildError("WordPress plugin template is missing")
        names = [config.plugin_slug, config.plugin_slug + ".zip", config.plugin_slug + ".build-report.json", config.plugin_slug + ".zip.sha256"]
        for name in names:
            if (config.output / name).exists():
                raise BuildError(f"Output already exists: {config.output / name}. Choose a new output directory; existing builds are never overwritten.")
        config.output.mkdir(parents=True, exist_ok=True)
        count = len(source.dimensions)
        unknown = [key for key in metadata.get("pages", {}) if int(key) > count]
        if unknown:
            raise BuildError(f"Metadata refers to nonexistent source pages: {', '.join(unknown)}")
        ratio = dominant_ratio(source.dimensions)
        warnings = []
        differing = [i + 1 for i, (width, height) in enumerate(source.dimensions) if abs(width / height / ratio - 1) > .01]
        if differing:
            warnings.append("Pages with different ratios were contained with background padding: " + ", ".join(map(str, differing)))
        with tempfile.TemporaryDirectory(prefix=".wpcf-build-", dir=config.output) as temporary:
            stage = Path(temporary)
            plugin = stage / config.plugin_slug
            # Preserve links during staging so they can be rejected, not followed.
            shutil.copytree(template, plugin, symlinks=True)
            for item in plugin.rglob("*"):
                if item.is_symlink():
                    raise BuildError("Plugin template cannot contain symlinks")
                if item.is_file() and item.suffix in {".php", ".txt", ".json"}:
                    value = item.read_text(encoding="utf-8-sig")
                    value = value.replace("__PLUGIN_NAME__", config.plugin_name).replace("__PLUGIN_SLUG__", config.plugin_slug).replace("__VERSION__", config.version)
                    item.write_text(value, encoding="utf-8")
            catalogue = plugin / "catalogues" / config.catalogue_slug
            (catalogue / "pages").mkdir(parents=True, exist_ok=True)
            (catalogue / "thumbs").mkdir(parents=True, exist_ok=True)
            pages = []
            for index in range(count):
                image, pdf_text = source.read(index, config.retina_long_edge)
                source_size = image.size
                try:
                    canvas = fit_canvas(image, ratio, config.retina_long_edge, config.background)
                finally:
                    image.close()
                number = index + 1
                stem = f"page-{number:03d}"
                standard = "pages/" + stem + ".webp"
                retina = "pages/" + stem + "-2x.webp"
                thumbnail = "thumbs/" + stem + ".webp"
                dimensions = save_variant(canvas, catalogue / standard, config.page_long_edge, config.quality)
                if max(canvas.size) > config.page_long_edge:
                    retina_dimensions = save_variant(canvas, catalogue / retina, config.retina_long_edge, config.quality)
                else:
                    retina = standard
                    retina_dimensions = dimensions
                save_variant(canvas, catalogue / thumbnail, config.thumb_long_edge, config.quality)
                page_metadata = metadata.get("pages", {}).get(str(number), {})
                links = transform_hotspots(page_metadata.get("links", []), source_size, canvas.size)
                canvas.close()
                pages.append({
                    "id": stem, "index": number, "width": dimensions[0], "height": dimensions[1],
                    "retinaWidth": retina_dimensions[0], "retinaHeight": retina_dimensions[1],
                    "src": standard, "src2x": retina, "thumbnail": thumbnail,
                    "title": page_metadata.get("title", f"Page {number}"),
                    "alt": page_metadata.get("alt", f"{config.catalogue_title}, page {number}"),
                    "text": page_metadata.get("searchText", pdf_text).strip(),
                    "links": links,
                })
            padded = bool(count % 2 and not config.no_pad_even)
            if padded:
                number = len(pages) + 1
                stem = f"page-{number:03d}"
                edge = config.page_long_edge
                width, height = (edge, round(edge / ratio)) if ratio >= 1 else (round(edge * ratio), edge)
                blank = Image.new("RGB", (max(1, width), max(1, height)), "#" + config.background)
                standard, thumbnail = f"pages/{stem}.webp", f"thumbs/{stem}.webp"
                size = save_variant(blank, catalogue / standard, edge, config.quality)
                save_variant(blank, catalogue / thumbnail, config.thumb_long_edge, config.quality)
                blank.close()
                pages.append({"id": stem, "index": number, "width": size[0], "height": size[1], "retinaWidth": size[0], "retinaHeight": size[1], "src": standard, "src2x": standard, "thumbnail": thumbnail, "title": "Back cover", "alt": "Blank back cover", "text": "", "links": [], "generatedBlank": True})
                warnings.append("A neutral blank back cover was appended to keep an even leaf count.")
            manifest = {"schemaVersion": 1, "title": config.catalogue_title, "description": metadata.get("description", ""), "aspectRatio": ratio, "pages": pages, "download": None}
            if config.include_pdf:
                shutil.copyfile(config.input, catalogue / "catalogue.pdf")
                manifest["download"] = "catalogue.pdf"
            write_json(catalogue / "manifest.json", manifest)
            zip_path = stage / (config.plugin_slug + ".zip")
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                for item in sorted(plugin.rglob("*")):
                    if item.is_file() and item.name != ".gitkeep":
                        archive.write(item, (Path(config.plugin_slug) / item.relative_to(plugin)).as_posix())
            validation = validate_package(zip_path)
            report = {"version": config.version, "sourceType": source_type, "sourcePages": count, "outputPages": len(pages), "blankBackCoverAdded": padded, "pageRatio": ratio, "pageLongEdge": config.page_long_edge, "retinaLongEdge": config.retina_long_edge, "thumbnailLongEdge": config.thumb_long_edge, "format": "WebP", "quality": config.quality, "warnings": warnings, "validation": validation, "shortcode": '[product_flipbook catalogue="' + config.catalogue_slug + '"]', "block": "Product Flipbook"}
            report_file = stage / (config.plugin_slug + ".build-report.json")
            write_json(report_file, report)
            hash_file = stage / (config.plugin_slug + ".zip.sha256")
            hash_file.write_text(validation["sha256"] + "  " + zip_path.name + "\n", encoding="ascii")
            # Move only completed, validated artifacts; never replace existing builds.
            for artifact in (plugin, zip_path, report_file, hash_file):
                if (config.output / artifact.name).exists():
                    raise BuildError("Output changed during build; refusing to overwrite it")
                shutil.move(str(artifact), str(config.output / artifact.name))
            return report
    finally:
        source.close()


def argument_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="PDF or directory of naturally ordered page images")
    parser.add_argument("--output", type=Path, required=True, help="New output location; existing matching builds are never overwritten")
    parser.add_argument("--plugin-name", default="WordPress PDF Catalogue Flipbook")
    parser.add_argument("--plugin-slug", default="wp-product-flipbook")
    parser.add_argument("--catalogue-title", default="Product Catalogue")
    parser.add_argument("--catalogue-slug", default="default")
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--page-long-edge", type=int, default=1600)
    parser.add_argument("--retina-long-edge", type=int, default=2400)
    parser.add_argument("--thumb-long-edge", type=int, default=320)
    parser.add_argument("--quality", type=int, default=88)
    parser.add_argument("--background", default="FFFFFF")
    parser.add_argument("--include-pdf", action="store_true")
    parser.add_argument("--no-pad-even", action="store_true")
    parser.add_argument("--version", default="1.0.1")
    return parser


def main() -> int:
    args = argument_parser().parse_args()
    try:
        report = build(BuildConfig(**vars(args)))
    except (BuildError, ValidationError, OSError, Image.DecompressionBombError) as error:
        print(f"Build failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("Plugin ZIP:", str(args.output.resolve() / (args.plugin_slug + ".zip")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
