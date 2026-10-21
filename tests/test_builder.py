"""Behavioral coverage for conversion, publication safety, and ZIP validation."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_wordpress_flipbook import BuildConfig, BuildError, build, fit_canvas, load_metadata, valid_link_url, transform_hotspots
from validate_wordpress_package import ValidationError, validate_package


def make_template(directory: Path):
    """A minimal real package fixture isolates builder tests from template edits."""
    fixture = {
        "wordpress-product-flipbook.php": "<?php\n/* Plugin Name: __PLUGIN_NAME__\nVersion: __VERSION__\n*/\n",
        "assets/js/viewer.js": "window.fixtureViewer = true;",
        "assets/css/viewer.css": ".wpcf { box-sizing: border-box; }",
        "assets/vendor/page-flip.browser.js": "window.fixturePageFlip = true;",
        "assets/vendor/page-flip.LICENSE": "Test fixture, not distributed vendor code.",
        "block/block.json": json.dumps({"name": "wpcf/product-flipbook"}),
        "block/editor.js": "window.fixtureEditor = true;",
        "LICENSE": "Original test fixture license.",
    }
    for name, text in fixture.items():
        target = directory / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def make_pdf(path: Path):
    """A tiny original, text-bearing PDF avoids a second PDF dependency."""
    stream = b"BT /F1 18 Tf 20 150 Td (SKU-DEMO-001 Backpack) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 150 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, content in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{number} 0 obj\n".encode() + content + b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.write_bytes(data)


class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.template = self.root / "template"
        make_template(self.template)
        self.source = self.root / "输入图像"
        self.source.mkdir()
        self.output = self.root / "结果"

    def tearDown(self):
        self.temporary.cleanup()

    def config(self, **kwargs):
        values = {"input": self.source, "output": self.output, "page_long_edge": 180, "retina_long_edge": 240, "thumb_long_edge": 48}
        values.update(kwargs)
        return BuildConfig(**values)

    def page(self, name="page-01.png", size=(150, 200), color="red"):
        target = self.source / name
        Image.new("RGB", size, color).save(target)
        return target

    def manifest(self):
        return json.loads((self.output / "wp-product-flipbook/catalogues/default/manifest.json").read_text("utf-8"))

    def test_real_image_build_natural_order_and_odd_back_cover(self):
        self.page("页-10.png", color="blue")
        self.page("页-2.png", color="green")
        first = self.page("页-1.png", color="red")
        original = first.read_bytes()
        report = build(self.config(catalogue_title="采购目录"), template=self.template)
        self.assertEqual(report["sourcePages"], 3)
        self.assertEqual(report["outputPages"], 4)
        self.assertTrue(report["blankBackCoverAdded"])
        self.assertEqual(first.read_bytes(), original)
        manifest = self.manifest()
        self.assertEqual(manifest["title"], "采购目录")
        self.assertTrue(manifest["pages"][-1]["generatedBlank"])
        page_file = self.output / "wp-product-flipbook/catalogues/default" / manifest["pages"][0]["src"]
        with Image.open(page_file) as image:
            red, green, blue = image.getpixel((50, 50))
            self.assertGreater(red, green + blue)
        validation = validate_package(self.output / "wp-product-flipbook.zip")
        self.assertEqual(validation["catalogues"], [{"slug": "default", "pages": 4}])
        self.assertEqual(len(validation["sha256"]), 64)
        self.assertNotIn(str(self.source), json.dumps(report))

    def test_small_raster_not_upscaled_and_original_ratio_contained(self):
        image = Image.new("RGB", (60, 30), "red")
        canvas = fit_canvas(image, .5, 2400, "FFFFFF")
        self.assertEqual(canvas.size, (30, 60))
        self.assertEqual(canvas.getpixel((15, 0)), (255, 255, 255))
        self.assertEqual(canvas.getpixel((15, 30)), (255, 0, 0))
        self.page(size=(60, 100))
        build(self.config(no_pad_even=True), self.template)
        page = self.manifest()["pages"][0]
        self.assertEqual((page["width"], page["height"]), (60, 100))
        self.assertEqual(page["src"], page["src2x"])
        self.assertEqual((page["retinaWidth"], page["retinaHeight"]), (60, 100))

    def test_mixed_ratios_use_padding_not_stretching(self):
        self.page("1.png", (120, 180))
        self.page("2.png", (120, 180))
        self.page("3.png", (180, 120))
        report = build(self.config(), self.template)
        self.assertTrue(any("3" in warning and "padding" in warning for warning in report["warnings"]))
        pages = self.manifest()["pages"]
        self.assertEqual(pages[0]["width"], pages[2]["width"])
        self.assertEqual(pages[0]["height"], pages[2]["height"])

    def test_high_resolution_variant_reports_actual_dimensions(self):
        self.page(size=(360, 480))
        build(self.config(no_pad_even=True), self.template)
        page = self.manifest()["pages"][0]
        self.assertEqual((page["width"], page["height"]), (135, 180))
        self.assertEqual((page["retinaWidth"], page["retinaHeight"]), (180, 240))
        self.assertNotEqual(page["src"], page["src2x"])

    def test_exif_orientation_is_respected(self):
        image = Image.new("RGB", (200, 100), "red")
        exif = image.getexif()
        exif[274] = 6
        image.save(self.source / "camera.jpg", exif=exif)
        build(self.config(no_pad_even=True), self.template)
        page = self.manifest()["pages"][0]
        self.assertEqual((page["width"], page["height"]), (90, 180))

    def test_corrupt_input_and_multiframe_fail_cleanly(self):
        bad = self.source / "bad.png"
        bad.write_bytes(b"This is not an image")
        with self.assertRaisesRegex(BuildError, "Cannot open image"):
            build(self.config(), self.template)
        bad.unlink()
        frames = [Image.new("RGB", (80, 100), color) for color in ("red", "blue")]
        frames[0].save(self.source / "multipage.tiff", save_all=True, append_images=frames[1:])
        with self.assertRaisesRegex(BuildError, "Multi-frame"):
            build(self.config(), self.template)

    def test_no_overwrite_of_existing_complete_build(self):
        self.page()
        build(self.config(), self.template)
        archive = self.output / "wp-product-flipbook.zip"
        original = archive.read_bytes()
        with self.assertRaisesRegex(BuildError, "already exists"):
            build(self.config(), self.template)
        self.assertEqual(archive.read_bytes(), original)

    def test_invalid_options_and_empty_input(self):
        with self.assertRaisesRegex(BuildError, "no supported"):
            build(self.config(), self.template)
        self.page()
        for options in ({"plugin_slug": "../escape"}, {"background": "red"}, {"quality": 101}, {"include_pdf": True}, {"plugin_name": "Bad */ ?>"}, {"output": self.source / "dist"}):
            with self.subTest(options=options), self.assertRaises(BuildError):
                build(self.config(**options), self.template)

    def test_metadata_search_and_links(self):
        self.page()
        metadata = self.root / "metadata.json"
        metadata.write_text(json.dumps({"description": "Neutral demo", "pages": {"1": {"title": "Backpack", "searchText": "SKU-001", "links": [{"x": 5, "y": 10, "width": 20, "height": 30, "url": "/product/demo/", "label": "View product"}]}}}), encoding="utf-8")
        build(self.config(metadata=metadata), self.template)
        page = self.manifest()["pages"][0]
        self.assertEqual(page["text"], "SKU-001")
        self.assertEqual(page["links"][0]["url"], "/product/demo/")

    def test_unsafe_metadata_and_nonexistent_page_fail(self):
        self.page()
        path = self.root / "metadata.json"
        for value in ("javascript:alert(1)", "//example.com", "file:///C:/private", "data:text/html,a", "https://user:password@example.com"):
            self.assertFalse(valid_link_url(value))
        path.write_text(json.dumps({"pages": {"99": {"title": "Missing page"}}}), encoding="utf-8")
        with self.assertRaisesRegex(BuildError, "nonexistent"):
            build(self.config(metadata=path), self.template)
        path.write_text(json.dumps({"pages": {"1": {"links": [{"x": 90, "y": 0, "width": 50, "height": 10, "url": "/demo/", "label": "Demo"}]}}}), encoding="utf-8")
        with self.assertRaisesRegex(BuildError, "outside"):
            load_metadata(path)

    def test_hotspots_follow_artwork_when_page_is_padded(self):
        links = [{"x": 0, "y": 0, "width": 100, "height": 100, "url": "/product/demo/", "label": "Demo"}]
        transformed = transform_hotspots(links, (100, 50), (100, 200))[0]
        self.assertEqual(transformed["x"], 0)
        self.assertEqual(transformed["y"], 37.5)
        self.assertEqual(transformed["width"], 100)
        self.assertEqual(transformed["height"], 25)
        self.assertEqual(links[0]["y"], 0)

    @unittest.skipUnless(importlib.util.find_spec("pypdfium2"), "pypdfium2 is not installed")
    def test_pdf_render_extract_text_and_optional_download(self):
        source = self.root / "产品.pdf"
        make_pdf(source)
        report = build(self.config(input=source, include_pdf=True), self.template)
        self.assertEqual(report["sourceType"], "pdf")
        manifest = self.manifest()
        self.assertIn("SKU-DEMO-001", manifest["pages"][0]["text"])
        self.assertEqual(manifest["download"], "catalogue.pdf")
        self.assertEqual((self.output / "wp-product-flipbook/catalogues/default/catalogue.pdf").read_bytes(), source.read_bytes())

    def test_zip_validation_detects_missing_asset_and_truncation(self):
        self.page()
        build(self.config(), self.template)
        archive = self.output / "wp-product-flipbook.zip"
        bad = self.root / "missing.zip"
        with zipfile.ZipFile(archive) as source, zipfile.ZipFile(bad, "w") as target:
            for entry in source.infolist():
                if not entry.filename.endswith("pages/page-001.webp"):
                    target.writestr(entry, source.read(entry))
        with self.assertRaisesRegex(ValidationError, "Missing src"):
            validate_package(bad)
        bad.write_bytes(archive.read_bytes()[:-80])
        with self.assertRaisesRegex(ValidationError, "Unreadable|truncated"):
            validate_package(bad)

    def test_zip_traversal_and_multiple_root_rejected(self):
        archive = self.root / "unsafe.zip"
        with zipfile.ZipFile(archive, "w") as target:
            target.writestr("plugin/../../escape.php", "bad")
        with self.assertRaisesRegex(ValidationError, "Unsafe"):
            validate_package(archive)
        with zipfile.ZipFile(archive, "w") as target:
            target.writestr("first/file.txt", "first")
            target.writestr("second/file.txt", "second")
        with self.assertRaisesRegex(ValidationError, "exactly one"):
            validate_package(archive)


if __name__ == "__main__":
    unittest.main()
