# WordPress integration

The ZIP contains one plugin root with `wordpress-product-flipbook.php`, local assets, a dynamic block, and `catalogues/default/manifest.json`. Upload the generated plugin ZIP, not this entire Skill source repository.

1. WordPress → Plugins → Add New → Upload Plugin → Activate.
2. Add a Product Flipbook block or a Shortcode block containing `[product_flipbook catalogue="default"]`.
3. Preview, then publish the page. Add the page to the site's navigation using the theme's navigation editor.
4. Check desktop and phone. If a cache plugin delays JavaScript, exclude the two `wpcf` viewer scripts and retest first-click behavior.

`mode="overlay"` opens a full reader; `mode="inline"` expands it in the page. Multiple instances on a page are supported. One generated bundle should be active per site because shortcode and block names are shared. For additional catalogues, copy a builder-generated catalogue directory under the same installed bundle's `catalogues/`, keeping its media paths relative, and use its slug. Include all catalogues when making an update.

The plugin does not automatically create pages, change navigation, rewrite URLs, change SEO plugins, or modify theme code. Deactivation leaves the page content intact; reactivation restores rendering. Bundled catalogue files are public static files.

## SEO and content

Use the WordPress page as the only public catalogue landing page. Add normal HTML category descriptions and product links outside the reader. The plugin uses no standalone index.html/iframe. Supply accurate product metadata; do not invent prices, reviews, or availability. Avoid duplicating H1 headings in the reader. User-requested navigation/page creation is a separate WordPress operation.

## Failure checks

- Unknown shortcode: plugin not active, wrong shortcode, or the source-repository ZIP was uploaded instead of a generated plugin ZIP.
- Missing pages: validate every manifest reference and check asset URLs in the browser network log.
- Loading error: check library dependency order and caching/minification. The reader offers retry and reports failure explicitly.
- Too large to upload: compare the ZIP size with `upload_max_filesize`, `post_max_size`, web-server limits, and available disk space. A theme upload cannot install this plugin.
- Distorted page: verify source ratio and use contain; do not force a page image to fill an unrelated CSS aspect ratio.

## Maintenance

Preserve the plugin slug and main filename for updates. Increment the version, rebuild separately, run the ZIP validator, then use WordPress's replace-plugin flow. Scripts, styles, manifest and page-image requests include the plugin version. Purge cached page HTML on the target site after an update; a proxy that discards query strings also needs a cache purge. Keep a backup until the updated viewer is tested. The viewer needs no database tables or external service credentials.
