# Testing and compatibility

Tests must run on the **exact generated plugin** as well as the source template.
A valid ZIP does not prove that WordPress activates it or the browser turns pages.

## Reproducible local checks

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p "test_*.py" -v
php -l assets/wordpress-plugin-template/wordpress-product-flipbook.php
php -l assets/wordpress-plugin-template/uninstall.php
php tests/test_wordpress_plugin.php
node --check assets/wordpress-plugin-template/assets/js/viewer.js
node --check assets/wordpress-plugin-template/block/editor.js
node scripts/patch_vendor.mjs --check
node tests/test_vendor_lifecycle.mjs
python scripts/build_wordpress_flipbook.py --input examples/demo/pages --metadata examples/demo/metadata.json --output dist/test-build --catalogue-title "Field Notes — Sample Catalogue"
python scripts/validate_wordpress_package.py dist/test-build/wp-product-flipbook.zip
```

Use a fresh output directory for repeat builds. `requirements.txt` is for building,
not for running WordPress. Node and PHP are developer test tools, not part of the
Python conversion pipeline.

## Real WordPress

Create a disposable WordPress installation with `WP_ENVIRONMENT_TYPE` set to
`local` or `development`. Install and activate the generated plugin with catalogue
`default`. Set `WPCF_WP_ROOT` to the absolute installation path. If necessary set
`WPCF_TEST_HOST` to its host and port. Run:

```bash
php tests/wp-integration-test.php
php tests/seed-wordpress.php
```

The integration suite tests registration, REST block rendering, shortcodes,
resource dependency ordering, escaping, catalogue validation, multiple instances,
admin permissions, and late-render CSS output/de-duplication. The seed script
creates clearly marked test pages; never use it against a production database.

## Browser

Install Playwright in your development environment, including its Chromium
browser. Set `WPCF_TEST_URL` to the seeded local WordPress URL (default
`http://127.0.0.1:8937`). Optionally set `WPCF_BROWSER` to a local Chromium/Edge
executable, and `WPCF_PLAYWRIGHT` to an absolute Playwright module directory when
using an existing installation. These variables are environment-specific and
should not be committed with local machine paths.

```bash
node tests/browser-smoke.cjs
node tests/browser-edge-cases.cjs
```

The browser tests use the twelve-page fictional demo and expect the seeded routes.
Screenshots and reports go under `dist/`; they are not private-site screenshots.
Inspect screenshots visually as well as reading assertions: check the cover,
desktop spread, right-page zoom, mobile portrait and mobile landscape. Long
catalogues and dense small print need additional tests with authorized real data.

## Recorded release checks

### 1.0.1 naming update

The Skill metadata and folder name, project documentation and default plugin
display name were updated. The plugin version is now 1.0.1; runtime identifiers
and reader behavior are unchanged. The 18 Python tests, 30 PHP contract checks,
Skill validation, JavaScript syntax, vendor checksum and rebuilt ZIP validation
were re-run successfully. The real WordPress/browser evidence below comes from
the initial release; those suites were not re-run for this naming-only update.

### Initial release

The initial release was checked locally with Python 3.12, Node 24, PHP 8.5.11,
WordPress reporting version 7.1.3 with SQLite, and Chromium-based Edge through
Playwright. Twenty Twenty-Five and a minimal classic test theme were exercised.
This isolated test site is not the user's live website.

- Python builder/validator/source-package suite: 18 tests passed.
- PHP contract suite: 30 checks passed.
- Actual WordPress integration: 38 checks passed.
- Browser smoke: 25 checks passed; desktop 1440×1000, mobile 390×844 at DPR 3,
  and rotated mobile 844×390. Screenshots visually inspected.
- Browser edge cases: 24 checks passed, including keyboard, modal focus/Escape,
  fullscreen enter/exit, reduced motion, CDP touch swipe, odd final spread,
  rapid close/reopen during loading, image failure, and no-JavaScript links.
  Both browser suites completed with zero uncaught page errors.
- Patched vendor lifecycle test: passed, including 50 destroy cycles with no
  residual animation-frame queue.

The template declares WordPress 6.2 / PHP 7.4 minimum targets, **not a tested
matrix**. Safari/iOS, Firefox, older WP/PHP versions, Multisite, object/page-cache
products, CDN rewriting, CSP policies and commercial page builders have not all
been tested. Test the actual deployment stack before claiming compatibility.
The GitHub Actions workflow is supplied; a local pass is not a completed cloud CI run.

## WordPress API references

The integration uses official [block registration](https://developer.wordpress.org/reference/functions/register_block_type/),
[script dependency registration](https://developer.wordpress.org/reference/functions/wp_enqueue_script/)
and [shortcode APIs](https://developer.wordpress.org/plugins/shortcodes/).
Additional code and licensing details are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
