# Security

The generated viewer is read-only and contains no upload, write or mail endpoint.
Catalogue files are public static assets, not protected downloads. Do not bundle
confidential documents. Source PDFs are included only with `--include-pdf`.

Only process PDFs and images you trust in a patched build environment. The
builder is not a sandbox for malicious documents. Keep Python dependencies and
WordPress current and test updates before deploying to production.

Report a vulnerability privately through the repository's GitHub security
advisory channel if the repository owner has enabled it. If it is unavailable,
ask the owner for a private contact without posting exploit details publicly.
Do not upload sensitive catalogues as a reproduction; make a synthetic fixture.

The maintainer should enable private vulnerability reporting in GitHub before
publishing. No response-time commitment is implied by this template.
