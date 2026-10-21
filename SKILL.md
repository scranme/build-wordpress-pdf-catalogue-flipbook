---
name: build-wordpress-pdf-catalogue-flipbook
description: "Turn finished catalogue PDFs or ordered page images into a self-contained WordPress flipbook plugin ZIP. Use for WordPress catalogue integration, shortcode or Gutenberg embedding, image clarity, page-ratio preservation, and plugin packaging repair. Not for editing the catalogue artwork or general photo albums."
---

# WordPress PDF Catalogue Flipbook Builder

Build an installable WordPress page-turning catalogue plugin from a finished product catalogue PDF or ordered page images. Chinese project name: WordPress PDF 产品目录翻页插件生成器.

Deliver a theme-independent WordPress plugin ZIP with a cover-first reader, local page-turn engine, Gutenberg block, and shortcode. Preserve supplied finished artwork and reading order. `SKILL_DIR` is this directory.

## Inputs and decisions

- Accept a PDF or an ordered folder of PNG/JPEG/WebP page images. Inspect the cover, a dense middle page, and the last page before choosing resolution.
- Read [conversion.md](references/conversion.md) for double-page source spreads, page sizing, mixed ratios, and metadata.
- Read [wordpress.md](references/wordpress.md) before packaging or diagnosing WordPress integration.
- The default is an independent plugin. Integrate into a theme only when explicitly requested, and preserve that theme's unrelated functionality.
- Source artwork, company PDFs, certificates, and customer data stay out of a public reusable Skill repository unless expressly authorized for publication.

## Build

Install `requirements.txt` into the chosen Python environment. Resolve script paths relative to this Skill directory. Quote all filesystem arguments.

```bash
python scripts/build_wordpress_flipbook.py --input catalogue.pdf --output dist --plugin-name "Product Catalogue" --catalogue-title "2027 Catalogue"
python scripts/validate_wordpress_package.py dist/wp-product-flipbook.zip
```

The builder copies the WordPress template, renders pages, makes responsive WebP variants and thumbnails, writes a manifest, packages one top-level plugin directory, and records the build. Use `--metadata metadata.json` for searchable titles/SKUs and product links. See `--help` for output sizing and source-PDF inclusion.

Do not use PDF page dimensions as CSS book dimensions. The runtime fits the book to available width and height and displays source artwork with `contain`. Do not enlarge a low-resolution raster and describe it as improved detail. PDF spread splitting requires a confirmed gutter/reading order; do not automatically split every landscape PDF.

## WordPress contract

- Install through Plugins → Add New → Upload Plugin; activation registers `[product_flipbook catalogue="default"]` and the Product Flipbook block.
- No theme patch, build toolchain, CDN script, external viewer, or manual PHP snippet is needed on the website.
- Keep one generated plugin bundle active per site; multiple books and multiple reader instances belong in that bundle. Updates preserve the plugin folder/filename and increment its version.
- Resolve assets through WordPress plugin URLs, validate catalogue slugs and manifest paths, escape server output, and use DOM text APIs for metadata.
- Prefix UI styles with `wpcf-`; load assets only when used. Verify late shortcode rendering and dynamic blocks, not just post-content detection.
- The visitor opens a cover; high-resolution neighboring pages are loaded progressively. Mobile uses a single-page view. Include recoverable loading errors and a retry action.
- Keep arrows, buttons, touch, page jump, thumbnails, search, close, zoom, fullscreen, focus restoration, and reduced-motion behavior usable.
- The viewer is read-only; do not introduce upload endpoints, email forms, or cached nonce dependencies.
- Let WordPress own the public URL, H1, canonical and descriptive HTML. Search inside a picture book is not an SEO substitute for product pages.

## Verify and hand off

Run the package validator against the exact ZIP to deliver. Run the included builder tests after conversion changes. For runtime changes, run the browser checks and, when available, actual WordPress integration tests. A ZIP check alone does not prove activation or animation works.

Read [TESTING.md](TESTING.md) when preparing a release or changing the integration; it gives the commands, disposable WordPress fixtures, browser checks and tested-versus-targeted compatibility boundaries.

Report output ZIP, page count, source-page treatment, shortcode/block, checks actually run, and any untested hosting conditions. The standard hosting upload limit may be smaller than a large catalogue; use hosting file access or ask the administrator to raise the limit instead of lowering page clarity without consent.

## Repair

First test archive integrity, plugin root/header, local library presence, manifest references, plugin activation, and shortcode registration. Then inspect network 404s, script order, JavaScript optimization, theme styles, and viewport sizing. Keep the original package; build the repair in a separate output. Never tell the visitor that loading succeeded if the reader did not initialize.
