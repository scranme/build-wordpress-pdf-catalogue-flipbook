# Contributing

Keep the project focused on finished catalogues and WordPress delivery. Preserve
page artwork and proportions. Prefer a plugin over edits to a user's theme.

Use a branch, explain the problem and include a reproducible test. Run Python
tests, PHP contract checks, JavaScript syntax checks and package validation.
Changes to reader behavior also need desktop/mobile browser checks; WordPress
changes need a disposable real WordPress installation, not only PHP stubs.

Never commit a user's artwork, email, credentials, database or website archive.
Use the fictional demo or a minimal generated fixture. Do not add telemetry,
external CDNs or network endpoints silently.

Do not edit the vendored engine casually. Record upstream version, patch intent
and checksums, preserve its license and include a regression test. See
`THIRD_PARTY_NOTICES.md` for provenance.

New options must be documented in the CLI help and relevant reference. Keep
`SKILL.md` concise; place operational detail in `references/`.
