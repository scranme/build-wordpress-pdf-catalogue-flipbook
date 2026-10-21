#!/usr/bin/env python3
"""Validate the exact generated WordPress ZIP, without extracting it."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile

from PIL import Image, UnidentifiedImageError


class ValidationError(ValueError):
    """A package violates the supported WordPress installation contract."""


REQUIRED_FILES = (
    "wordpress-product-flipbook.php",
    "assets/js/viewer.js",
    "assets/css/viewer.css",
    "assets/vendor/page-flip.browser.js",
    "assets/vendor/page-flip.LICENSE",
    "block/block.json",
    "block/editor.js",
    "LICENSE",
)
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def safe_relative(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValidationError(f"Invalid relative path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in value.split("/")):
        raise ValidationError(f"Unsafe relative path: {value!r}")
    if ":" in value or "?" in value or "#" in value:
        raise ValidationError(f"Only local file paths are supported: {value!r}")
    return value


def check_manifest(manifest: object, prefix: str, files: set[str], read) -> int:
    if not isinstance(manifest, dict) or manifest.get("schemaVersion") != 1:
        raise ValidationError("Manifest requires schemaVersion: 1")
    if not isinstance(manifest.get("title"), str) or not manifest["title"].strip():
        raise ValidationError("Manifest requires a nonempty title")
    ratio = manifest.get("aspectRatio")
    if not isinstance(ratio, (int, float)) or isinstance(ratio, bool) or not math.isfinite(ratio) or ratio <= 0:
        raise ValidationError("Manifest aspectRatio must be a finite positive number")
    pages = manifest.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ValidationError("Manifest pages must be a nonempty array")
    ids: set[str] = set()
    checked_images: dict[str, tuple[int, int]] = {}
    for number, page in enumerate(pages, 1):
        if not isinstance(page, dict) or page.get("index") != number:
            raise ValidationError(f"Page {number} has an invalid sequential index")
        page_id = page.get("id")
        if not isinstance(page_id, str) or not page_id or page_id in ids:
            raise ValidationError(f"Page {number} has a missing or duplicate id")
        ids.add(page_id)
        for dimension in ("width", "height"):
            value = page.get(dimension)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValidationError(f"Page {number} has invalid {dimension}")
        for field in ("src", "src2x", "thumbnail"):
            reference = prefix + safe_relative(page.get(field))
            if reference not in files:
                raise ValidationError(f"Missing {field} asset on page {number}: {reference}")
            if not read(reference):
                raise ValidationError(f"Empty page asset: {reference}")
            if reference not in checked_images:
                try:
                    with Image.open(io.BytesIO(read(reference))) as image:
                        image.load()
                        checked_images[reference] = image.size
                except (UnidentifiedImageError, OSError, ValueError) as error:
                    raise ValidationError(f"Invalid page image: {reference}") from error
            if field == "src" and checked_images[reference] != (page["width"], page["height"]):
                raise ValidationError(f"Page {number} dimensions do not match its image")
            if field == "src2x" and ("retinaWidth" in page or "retinaHeight" in page):
                if checked_images[reference] != (page.get("retinaWidth"), page.get("retinaHeight")):
                    raise ValidationError(f"Page {number} retina dimensions do not match its image")
    if manifest.get("download"):
        reference = prefix + safe_relative(manifest["download"])
        if reference not in files or not read(reference).startswith(b"%PDF-"):
            raise ValidationError("The optional download must reference an included PDF")
    return len(pages)


def validate_package(zip_path: Path | str) -> dict:
    zip_path = Path(zip_path)
    if not zip_path.is_file():
        raise ValidationError(f"ZIP does not exist: {zip_path}")
    try:
        with zipfile.ZipFile(zip_path) as archive:
            infos = archive.infolist()
            if not infos:
                raise ValidationError("ZIP is empty")
            files: set[str] = set()
            roots: set[str] = set()
            for info in infos:
                name = info.filename.rstrip("/")
                safe_relative(name)
                if info.flag_bits & 1:
                    raise ValidationError("Encrypted ZIP entries are not installable")
                if (info.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValidationError("ZIP symlinks are not supported")
                roots.add(name.split("/")[0])
                if not info.is_dir():
                    if name in files:
                        raise ValidationError(f"Duplicate ZIP entry: {name}")
                    files.add(name)
            if len(roots) != 1 or not SLUG.fullmatch(next(iter(roots))):
                raise ValidationError("ZIP must have exactly one slug-named plugin root")
            root = next(iter(roots)) + "/"
            for required in REQUIRED_FILES:
                if root + required not in files or not archive.read(root + required):
                    raise ValidationError(f"Missing required plugin file: {required}")
            php = archive.read(root + REQUIRED_FILES[0]).decode("utf-8-sig")
            if not re.search(r"Plugin Name:\s*\S", php[:8192]):
                raise ValidationError("Main PHP file lacks a WordPress Plugin Name header")
            if any(token in php for token in ("__PLUGIN_NAME__", "__PLUGIN_SLUG__", "__VERSION__")):
                raise ValidationError("Plugin PHP still contains build placeholders")
            corrupt = archive.testzip()
            if corrupt:
                raise ValidationError(f"ZIP checksum failed: {corrupt}")
            manifests = sorted(name for name in files if re.fullmatch(re.escape(root) + r"catalogues/[a-z0-9-]+/manifest\.json", name))
            if not manifests:
                raise ValidationError("Package contains no catalogue manifest")
            catalogues = []
            for name in manifests:
                try:
                    manifest = json.loads(archive.read(name).decode("utf-8-sig"))
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise ValidationError(f"Invalid manifest JSON: {name}") from error
                count = check_manifest(manifest, name.rsplit("/", 1)[0] + "/", files, archive.read)
                catalogues.append({"slug": name.split("/")[-2], "pages": count})
            block = json.loads(archive.read(root + "block/block.json"))
            if block.get("name") != "wpcf/product-flipbook":
                raise ValidationError("The Gutenberg block name must be wpcf/product-flipbook")
    except (zipfile.BadZipFile, EOFError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValidationError(f"Unreadable or truncated ZIP: {error}") from error
    return {
        "valid": True,
        "pluginRoot": root.rstrip("/"),
        "files": len(files),
        "catalogues": catalogues,
        "bytes": zip_path.stat().st_size,
        "sha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "checks": ["zip-crc", "single-plugin-root", "plugin-header", "local-runtime", "gutenberg-block", "manifest-and-assets"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip", type=Path)
    args = parser.parse_args()
    try:
        result = validate_package(args.zip)
    except (OSError, ValidationError) as error:
        print(f"Validation failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
