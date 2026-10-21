# Third-party notices and provenance

The Skill instructions, builder, WordPress integration and reader controls in this
repository are independently written. This is not an official release or fork of
`HaichaoLihc/create-photo-flipbook-ui`. That project inspired the use case; none of
its Skill text, application code or example photographs is redistributed here.

## Bundled browser dependency

- StPageFlip (`page-flip`), version **2.0.7**, by Nodlik; MIT.
- Upstream: https://github.com/Nodlik/StPageFlip
- Distribution: https://registry.npmjs.org/page-flip/-/page-flip-2.0.7.tgz
- Retrieved with `npm pack page-flip@2.0.7 --ignore-scripts`.
- Locally patched file: `assets/wordpress-plugin-template/assets/vendor/page-flip.browser.js`.
- Original distribution SHA-256: `bbaca0bbef57a22bb66a3fc69d67baf9a17fb9a9c89ec9ed35e2b91abe4bd1e7`.
- Patched distribution SHA-256: `09c07732ff868f0c3c3792df0eeb46b414a98a32a9f976fad4a2d75aad6af220`.
- License retained beside it as `page-flip.LICENSE`, including in generated plugins.

The local lifecycle patch makes the renderer retain and cancel its animation-frame
handle, guards against callbacks after stopping, and makes `PageFlip.destroy()`
stop rendering before removing its UI. Upstream 2.0.7 otherwise leaves its render
loop running after destruction. No page-turn geometry or visual styling is changed.
`scripts/patch_vendor.mjs` reproduces the two exact replacements, checks the original
and resulting SHA-256 values, and refuses unknown input. Run it on the original npm
file to reproduce the bundled version, or use `node scripts/patch_vendor.mjs --check`
to verify the checked-in file. `node tests/test_vendor_lifecycle.mjs` exercises the
actual bundled classes with a deterministic animation-frame scheduler.

No CDN is contacted by the reader. Update this dependency deliberately, preserve
its license, review/rebase this patch, update both checksums and re-run lifecycle
and browser tests before a release.

## Build/test dependencies

Pillow and pypdfium2 are installed separately from `requirements.txt`; they are
not embedded in generated plugins. Their own licenses and bundled-library notices
apply. In particular, pypdfium2 distributions contain PDFium third-party notices.
Playwright is an optional development dependency, not a WordPress runtime dependency.

## Catalogue content

The generated geometric demo is original and covered by this repository's MIT
license. User-supplied catalogue artwork, trademarks and source PDFs remain the
property of their respective rights holders and are not relicensed by the builder.
