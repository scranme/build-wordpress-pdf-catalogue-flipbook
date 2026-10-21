# Publish your repository

Project title: **WordPress PDF Catalogue Flipbook Builder**.
Chinese title: **WordPress PDF 产品目录翻页插件生成器**.
Repository name: `build-wordpress-pdf-catalogue-flipbook`.
Suggested description: `Turn product catalogue PDFs or page images into installable WordPress flipbook plugins with Gutenberg blocks and shortcodes. Built as a Codex skill.`
Suggested topics: `codex-skill`, `wordpress`, `flipbook`, `pdf`, `product-catalogue`.

## Before the first push

1. Read the license and third-party notices. Keep both when redistributing.
2. Review every file. Do not publish private PDFs, company builds, secrets, local
   WordPress databases, customer data or screenshots of private sites.
3. Generate the fictional demo and run the tests in `TESTING.md`.
4. Create an empty repository under your GitHub account. Choose public only if
   that is your intent. This project does not create or publish it automatically.
5. Upload the **contents** of this source folder so `README.md` and `SKILL.md`
   sit at the repository root. Do not upload the outer ZIP as your only source.

If using Git locally, run these commands inside this source directory:

```bash
git init
git add .
git diff --cached --stat
git status
# Review the staged files before continuing.
git commit -m "Publish WordPress PDF Catalogue Flipbook Builder"
git branch -M main
git remote add origin <YOUR_ACTUAL_GITHUB_REPOSITORY_URL>
git push -u origin main
```

Replace the placeholder with your own repository URL; it is not a usable command
as written. Git identity/credentials are configured by you, not bundled here.

## Releases

- Use semantic version tags, e.g. `v1.0.1`, after the main CI workflow passes.
- A GitHub release automatically has source archives. Optionally attach the
  generated **fictional demo** WordPress plugin ZIP and its SHA-256 file.
- Name source and plugin assets clearly: the source package is not installable
  through WordPress's Upload Plugin form.
- Update CHANGELOG and test coverage for each release. Increment the generated
  plugin's `--version` when delivering an update so browsers invalidate assets.
- Never attach a real company catalogue unless you hold publication rights and
  intend every bundled page and PDF to be publicly downloadable.

The CI workflow uploads a demo plugin as an Actions artifact; it does not create
releases, push commits, deploy sites or publish private inputs.
