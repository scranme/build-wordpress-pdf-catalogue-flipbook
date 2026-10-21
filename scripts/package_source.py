#!/usr/bin/env python3
"""Package reviewed public source only, never arbitrary working-directory files.

Maintain ALLOWLIST when intentionally adding public files. The resulting archive
is a GitHub/Codex source bundle, NOT an installable WordPress plugin. Existing ZIP
and checksum files are never overwritten. --list-only performs no writes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile


ROOT_NAME = "build-wordpress-pdf-catalogue-flipbook"
REPO = Path(__file__).resolve().parents[1]
ALLOWLIST = (
    ".github/workflows/ci.yml",
    ".gitignore",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "PUBLISHING.md",
    "README.md",
    "README.zh-CN.md",
    "SECURITY.md",
    "SKILL.md",
    "TESTING.md",
    "THIRD_PARTY_NOTICES.md",
    "agents/openai.yaml",
    "requirements.txt",
    "references/conversion.md",
    "references/wordpress.md",
    "scripts/build_wordpress_flipbook.py",
    "scripts/generate_demo_pages.py",
    "scripts/package_source.py",
    "scripts/patch_vendor.mjs",
    "scripts/validate_wordpress_package.py",
    "tests/test_builder.py",
    "tests/test_package_source.py",
    "tests/test_vendor_lifecycle.mjs",
    "tests/test_wordpress_plugin.php",
    "tests/wp-integration-test.php",
    "tests/seed-wordpress.php",
    "tests/browser-smoke.cjs",
    "tests/browser-edge-cases.cjs",
    "examples/preview-desktop.png",
    "examples/preview-mobile.png",
    "assets/wordpress-plugin-template/LICENSE",
    "assets/wordpress-plugin-template/readme.txt",
    "assets/wordpress-plugin-template/uninstall.php",
    "assets/wordpress-plugin-template/wordpress-product-flipbook.php",
    "assets/wordpress-plugin-template/assets/css/viewer.css",
    "assets/wordpress-plugin-template/assets/js/viewer.js",
    "assets/wordpress-plugin-template/assets/vendor/page-flip.browser.js",
    "assets/wordpress-plugin-template/assets/vendor/page-flip.LICENSE",
    "assets/wordpress-plugin-template/block/block.json",
    "assets/wordpress-plugin-template/block/editor.js",
    "examples/demo/metadata.json",
) + tuple(f"examples/demo/pages/page-{index:03d}.png" for index in range(1, 13))

REQUIRED_SOURCE_FILES = {
    "README.md", "SKILL.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "requirements.txt",
    ".github/workflows/ci.yml", "agents/openai.yaml",
    "scripts/build_wordpress_flipbook.py", "scripts/package_source.py",
    "scripts/validate_wordpress_package.py", "scripts/patch_vendor.mjs",
    "assets/wordpress-plugin-template/wordpress-product-flipbook.php",
    "assets/wordpress-plugin-template/assets/css/viewer.css",
    "assets/wordpress-plugin-template/assets/js/viewer.js",
    "assets/wordpress-plugin-template/assets/vendor/page-flip.browser.js",
    "assets/wordpress-plugin-template/assets/vendor/page-flip.LICENSE",
    "assets/wordpress-plugin-template/block/block.json",
    "assets/wordpress-plugin-template/block/editor.js",
    "examples/demo/metadata.json",
} | {f"examples/demo/pages/page-{index:03d}.png" for index in range(1, 13)}

EXCLUDED_PARTS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules", "dist", "cache", "tmp", "temp", "generated", "screenshots"}


class SourcePackageError(ValueError):
    """Source cannot safely be packaged with the public release contract."""


def collect_files(repo: Path) -> list[tuple[str, Path]]:
    repo = repo.resolve()
    if not repo.is_dir():
        raise SourcePackageError("Source repository directory does not exist")
    selected = []
    for name in sorted(ALLOWLIST):
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or any(part.casefold() in EXCLUDED_PARTS for part in relative.parts):
            raise SourcePackageError(f"Unsafe allowlist entry: {name}")
        target = repo / relative
        # Check every path component: a linked directory must not expose private data.
        for part in (target, *target.parents):
            if part == repo:
                break
            if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
                raise SourcePackageError(f"Linked source paths are not publishable: {name}")
        if target.is_file():
            if not target.resolve().is_relative_to(repo):
                raise SourcePackageError(f"Source escapes repository: {name}")
            selected.append((name, target))
        elif name in REQUIRED_SOURCE_FILES:
            raise SourcePackageError(f"Required public source file is missing: {name}")
    if len({name for name, _ in selected}) != len(selected):
        raise SourcePackageError("The source allowlist contains duplicate entries")
    return selected


def package(repo: Path, output: Path) -> dict:
    files = collect_files(repo)
    output = output.absolute()
    checksum = output.with_name(output.name + ".sha256")
    if output.suffix.lower() != ".zip":
        raise SourcePackageError("Output filename must end in .zip")
    if output.exists() or output.is_symlink() or checksum.exists() or checksum.is_symlink():
        raise SourcePackageError("Output ZIP or checksum already exists; choose a new filename")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".wpcf-source-", dir=output.parent) as temporary:
        staged = Path(temporary) / "source.zip"
        with zipfile.ZipFile(staged, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, path in files:
                # Fixed timestamps and permissions make byte-identical source reproducible.
                info = zipfile.ZipInfo(ROOT_NAME + "/" + name, date_time=(2026, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes(), compresslevel=9)
        with zipfile.ZipFile(staged) as archive:
            corrupt = archive.testzip()
            expected = {ROOT_NAME + "/" + name for name, _ in files}
            if corrupt or set(archive.namelist()) != expected:
                raise SourcePackageError("Source ZIP failed checksum or allowlist verification")
        digest = hashlib.sha256(staged.read_bytes()).hexdigest()
        created = []
        try:
            # Exclusive creation avoids replacing a file that appeared while packaging.
            with output.open("xb") as target, staged.open("rb") as source:
                created.append(output)
                shutil.copyfileobj(source, target)
            with checksum.open("x", encoding="ascii") as target:
                created.append(checksum)
                target.write(digest + "  " + output.name + "\n")
        except Exception:
            for path in created:
                path.unlink(missing_ok=True)
            raise
    return {"root": ROOT_NAME, "files": len(files), "bytes": output.stat().st_size, "sha256": digest, "crcValid": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO, help="Repository root (defaults to this script's parent)")
    parser.add_argument("--output", type=Path, help="New source ZIP filename, never overwritten")
    parser.add_argument("--list-only", action="store_true", help="Validate and list selected files without writing an archive")
    args = parser.parse_args()
    if not args.list_only and not args.output:
        parser.error("--output is required unless --list-only is used")
    if args.list_only and args.output:
        parser.error("Choose either --list-only or --output")
    try:
        if args.list_only:
            result = {"root": ROOT_NAME, "files": [name for name, _ in collect_files(args.repo)]}
        else:
            result = package(args.repo, args.output)
    except (OSError, SourcePackageError, zipfile.BadZipFile) as error:
        print(f"Source packaging failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
