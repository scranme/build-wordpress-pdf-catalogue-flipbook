<?php
/**
 * Plugin Name: __PLUGIN_NAME__
 * Description: A locally bundled product catalogue with a cover, page turning, search and accessible controls.
 * Version: __VERSION__
 * Requires at least: 6.2
 * Requires PHP: 7.4
 * Author: WordPress PDF Catalogue Flipbook contributors
 * License: MIT
 * Text Domain: wordpress-product-flipbook
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

// One generated bundle per site. Multiple catalogues and instances share this engine.
if ( ! class_exists( 'WPCF_Plugin', false ) ) {
    final class WPCF_Plugin {
        const VERSION = '__VERSION__';
        private static $manifest_cache = array();

        public static function boot() {
            add_action( 'init', array( __CLASS__, 'register' ) );
            add_action( 'wp_enqueue_scripts', array( __CLASS__, 'enqueue_for_content' ) );
            add_action( 'admin_menu', array( __CLASS__, 'admin_menu' ) );
            add_action( 'enqueue_block_editor_assets', array( __CLASS__, 'editor_data' ) );
        }

        public static function register() {
            self::register_assets();
            add_shortcode( 'product_flipbook', array( __CLASS__, 'render' ) );
            register_block_type(
                __DIR__ . '/block',
                array( 'render_callback' => array( __CLASS__, 'render_block' ) )
            );
        }

        public static function register_assets() {
            $base = plugin_dir_url( __FILE__ );
            wp_register_style( 'wpcf-style', $base . 'assets/css/viewer.css', array(), self::VERSION );
            // Footer dependency ordering works on WordPress 6.2 without newer strategy APIs.
            wp_register_script( 'wpcf-page-flip', $base . 'assets/vendor/page-flip.browser.js', array(), self::VERSION, true );
            wp_register_script( 'wpcf-runtime', $base . 'assets/js/viewer.js', array( 'wpcf-page-flip' ), self::VERSION, true );
            wp_register_script(
                'wpcf-block-editor',
                $base . 'block/editor.js',
                array( 'wp-blocks', 'wp-element', 'wp-block-editor', 'wp-components', 'wp-i18n' ),
                self::VERSION,
                true
            );
        }

        public static function enqueue_for_content() {
            if ( is_admin() ) {
                return;
            }
            $post = get_queried_object();
            if ( $post instanceof WP_Post && (
                has_shortcode( $post->post_content, 'product_flipbook' ) ||
                has_block( 'wpcf/product-flipbook', $post )
            ) ) {
                self::enqueue();
            }
        }

        private static function enqueue() {
            // Also supports render calls from widgets, templates and page builders.
            if ( ! wp_script_is( 'wpcf-runtime', 'registered' ) ) {
                self::register_assets();
            }
            wp_enqueue_style( 'wpcf-style' );
            wp_enqueue_script( 'wpcf-runtime' );
        }

        private static function valid_slug( $slug ) {
            return is_string( $slug ) && 1 === preg_match( '/^[a-z0-9][a-z0-9_-]{0,63}$/D', $slug );
        }

        /** Return a local public asset URL, never an absolute path or external URL. */
        private static function asset_url( $slug, $relative, $extensions ) {
            if ( ! self::valid_slug( $slug ) || ! is_string( $relative ) || '' === $relative ) {
                return '';
            }
            if ( preg_match( '/[\\\\\\x00-\\x20:#?%]/', $relative ) || '/' === $relative[0] ) {
                return '';
            }
            $parts = explode( '/', $relative );
            foreach ( $parts as $part ) {
                if ( '' === $part || '.' === $part || '..' === $part ) {
                    return '';
                }
            }
            if ( ! in_array( strtolower( pathinfo( $relative, PATHINFO_EXTENSION ) ), $extensions, true ) ) {
                return '';
            }
            $root = realpath( __DIR__ . '/catalogues/' . $slug );
            $file = realpath( __DIR__ . '/catalogues/' . $slug . '/' . $relative );
            if ( ! $root || ! $file || ! is_file( $file ) || 0 !== strpos( $file, $root . DIRECTORY_SEPARATOR ) ) {
                return '';
            }
            return plugin_dir_url( __FILE__ ) . 'catalogues/' . rawurlencode( $slug ) . '/' . implode( '/', array_map( 'rawurlencode', $parts ) ) . '?ver=' . rawurlencode( self::VERSION );
        }

        /** Load and validate the manifest used by the cover and editor. */
        public static function catalogue( $slug ) {
            if ( ! self::valid_slug( $slug ) ) {
                return new WP_Error( 'wpcf_slug', __( 'Invalid catalogue identifier.', 'wordpress-product-flipbook' ) );
            }
            if ( isset( self::$manifest_cache[ $slug ] ) ) {
                return self::$manifest_cache[ $slug ];
            }
            $base = realpath( __DIR__ . '/catalogues' );
            $path = realpath( __DIR__ . '/catalogues/' . $slug . '/manifest.json' );
            if ( ! $base || ! $path || 0 !== strpos( $path, $base . DIRECTORY_SEPARATOR ) || ! is_readable( $path ) || filesize( $path ) > 10 * 1024 * 1024 ) {
                return new WP_Error( 'wpcf_missing', __( 'Catalogue not found. Check its identifier in Settings → Product Flipbook.', 'wordpress-product-flipbook' ) );
            }
            $data = json_decode( file_get_contents( $path ), true );
            if ( ! is_array( $data ) || ! isset( $data['schemaVersion'] ) || 1 !== $data['schemaVersion'] || empty( $data['pages'] ) || ! is_array( $data['pages'] ) || array_keys( $data['pages'] ) !== range( 0, count( $data['pages'] ) - 1 ) ) {
                return new WP_Error( 'wpcf_manifest', __( 'This catalogue could not be read. Rebuild and validate the plugin package.', 'wordpress-product-flipbook' ) );
            }
            $extensions = array( 'jpg', 'jpeg', 'png', 'webp', 'avif' );
            foreach ( $data['pages'] as &$page ) {
                if ( ! is_array( $page ) ) {
                    return new WP_Error( 'wpcf_page', __( 'A catalogue page is missing.', 'wordpress-product-flipbook' ) );
                }
                $page['_src_url'] = self::asset_url( $slug, $page['src'] ?? '', $extensions );
                if ( '' === $page['_src_url'] ) {
                    return new WP_Error( 'wpcf_page', __( 'A catalogue image is missing. Rebuild and validate the plugin package.', 'wordpress-product-flipbook' ) );
                }
                $page['_thumb_url'] = self::asset_url( $slug, $page['thumbnail'] ?? '', $extensions );
            }
            unset( $page );
            $data['_manifest_url'] = plugin_dir_url( __FILE__ ) . 'catalogues/' . rawurlencode( $slug ) . '/manifest.json?ver=' . rawurlencode( self::VERSION );
            $data['_download_url'] = self::asset_url( $slug, $data['download'] ?? '', array( 'pdf' ) );
            self::$manifest_cache[ $slug ] = $data;
            return $data;
        }

        public static function render_block( $attributes ) {
            return self::render( $attributes );
        }

        public static function render( $attributes = array() ) {
            $attributes = shortcode_atts( array( 'catalogue' => 'default', 'mode' => 'overlay' ), is_array( $attributes ) ? $attributes : array(), 'product_flipbook' );
            $slug = $attributes['catalogue'];
            $data = self::catalogue( $slug );
            if ( is_wp_error( $data ) ) {
                return '<p class="wpcf-error" role="status">' . esc_html( $data->get_error_message() ) . '</p>';
            }
            self::enqueue();
            $mode = 'inline' === $attributes['mode'] ? 'inline' : 'overlay';
            $title = isset( $data['title'] ) && is_string( $data['title'] ) ? $data['title'] : __( 'Product catalogue', 'wordpress-product-flipbook' );
            $description = isset( $data['description'] ) && is_string( $data['description'] ) ? $data['description'] : '';
            $cover = $data['pages'][0];
            $id = wp_unique_id( 'wpcf-' );
            $label_id = $id . '-title';
            ob_start();
            // A late-rendered shortcode must not produce an unstyled cover. WP tracks done handles.
            if ( did_action( 'wp_head' ) && ! wp_style_is( 'wpcf-style', 'done' ) ) {
                wp_print_styles( array( 'wpcf-style' ) );
            }
            ?>
            <div id="<?php echo esc_attr( $id ); ?>" class="wpcf" data-wpcf data-manifest="<?php echo esc_url( $data['_manifest_url'] ); ?>" data-mode="<?php echo esc_attr( $mode ); ?>" data-title="<?php echo esc_attr( $title ); ?>">
                <div class="wpcf-cover">
                    <button type="button" class="wpcf-cover-button" data-wpcf-open aria-label="<?php echo esc_attr( sprintf( __( 'Open %s', 'wordpress-product-flipbook' ), $title ) ); ?>">
                        <img class="wpcf-cover-image" src="<?php echo esc_url( $cover['_src_url'] ); ?>" alt="<?php echo esc_attr( isset( $cover['alt'] ) && is_string( $cover['alt'] ) ? $cover['alt'] : $title ); ?>" width="<?php echo esc_attr( max( 1, (int) ( $cover['width'] ?? 600 ) ) ); ?>" height="<?php echo esc_attr( max( 1, (int) ( $cover['height'] ?? 840 ) ) ); ?>" loading="lazy" decoding="async">
                        <span class="wpcf-cover-action"><?php esc_html_e( 'Open catalogue', 'wordpress-product-flipbook' ); ?></span>
                    </button>
                    <div class="wpcf-cover-copy">
                        <h2 id="<?php echo esc_attr( $label_id ); ?>" class="wpcf-title"><?php echo esc_html( $title ); ?></h2>
                        <?php if ( '' !== $description ) : ?><p class="wpcf-description"><?php echo esc_html( $description ); ?></p><?php endif; ?>
                        <p class="wpcf-page-count"><?php echo esc_html( sprintf( __( '%d pages · Click the cover to browse', 'wordpress-product-flipbook' ), count( $data['pages'] ) ) ); ?></p>
                        <?php if ( $data['_download_url'] ) : ?><a class="wpcf-download" href="<?php echo esc_url( $data['_download_url'] ); ?>" download><?php esc_html_e( 'Download PDF', 'wordpress-product-flipbook' ); ?></a><?php endif; ?>
                    </div>
                </div>
                <p class="wpcf-status" data-wpcf-status role="status" aria-live="polite"></p>
                <noscript><p><?php esc_html_e( 'Enable JavaScript for page turning, or browse the page images below.', 'wordpress-product-flipbook' ); ?></p></noscript>
                <details class="wpcf-fallback">
                    <summary><?php esc_html_e( 'Browse individual page images', 'wordpress-product-flipbook' ); ?></summary>
                    <ol>
                        <?php foreach ( $data['pages'] as $number => $page ) : ?>
                            <li><a href="<?php echo esc_url( $page['_src_url'] ); ?>"><?php echo esc_html( sprintf( __( 'Page %d', 'wordpress-product-flipbook' ), $number + 1 ) . ( ! empty( $page['title'] ) && is_string( $page['title'] ) ? ' — ' . $page['title'] : '' ) ); ?></a></li>
                        <?php endforeach; ?>
                    </ol>
                </details>
            </div>
            <?php
            return ob_get_clean();
        }

        public static function catalogue_list() {
            $result = array();
            $files = glob( __DIR__ . '/catalogues/*/manifest.json' );
            foreach ( $files ?: array() as $file ) {
                $slug = basename( dirname( $file ) );
                $data = self::catalogue( $slug );
                if ( ! is_wp_error( $data ) ) {
                    $result[] = array( 'value' => $slug, 'label' => is_string( $data['title'] ?? null ) ? $data['title'] : $slug, 'pages' => count( $data['pages'] ) );
                }
            }
            return $result;
        }

        public static function editor_data() {
            wp_add_inline_script( 'wpcf-block-editor', 'window.WPCFCatalogues = ' . wp_json_encode( self::catalogue_list() ) . ';', 'before' );
        }

        public static function admin_menu() {
            add_options_page( __( 'Product Flipbook', 'wordpress-product-flipbook' ), __( 'Product Flipbook', 'wordpress-product-flipbook' ), 'manage_options', 'wpcf-catalogues', array( __CLASS__, 'admin_page' ) );
        }

        public static function admin_page() {
            if ( ! current_user_can( 'manage_options' ) ) {
                return;
            }
            ?>
            <div class="wrap">
                <h1><?php esc_html_e( 'Product Flipbook', 'wordpress-product-flipbook' ); ?></h1>
                <p><?php esc_html_e( 'Add the Product Flipbook block to any page, or paste a shortcode below into a Shortcode block. Use the page title and surrounding text for your catalogue introduction. Add the published page to navigation from the Site Editor or Appearance → Menus.', 'wordpress-product-flipbook' ); ?></p>
                <p><?php esc_html_e( 'No theme editing is required. Keep one generated flipbook plugin active; that bundle can contain several catalogue folders and any number of page instances.', 'wordpress-product-flipbook' ); ?></p>
                <table class="widefat striped"><thead><tr><th><?php esc_html_e( 'Catalogue', 'wordpress-product-flipbook' ); ?></th><th><?php esc_html_e( 'Pages', 'wordpress-product-flipbook' ); ?></th><th><?php esc_html_e( 'Shortcode', 'wordpress-product-flipbook' ); ?></th></tr></thead><tbody>
                    <?php $catalogues = self::catalogue_list(); ?>
                    <?php foreach ( $catalogues as $catalogue ) : ?>
                        <tr><td><?php echo esc_html( $catalogue['label'] ); ?></td><td><?php echo esc_html( $catalogue['pages'] ); ?></td><td><input readonly class="large-text code" aria-label="<?php esc_attr_e( 'Select and copy shortcode', 'wordpress-product-flipbook' ); ?>" value="<?php echo esc_attr( '[product_flipbook catalogue="' . $catalogue['value'] . '"]' ); ?>"></td></tr>
                    <?php endforeach; ?>
                    <?php if ( ! $catalogues ) : ?><tr><td colspan="3"><?php esc_html_e( 'No valid catalogues were found. Build and validate a plugin ZIP before installing.', 'wordpress-product-flipbook' ); ?></td></tr><?php endif; ?>
                </tbody></table>
                <p><?php esc_html_e( 'Optional: add mode="inline" to expand the reader inside the page instead of opening an overlay.', 'wordpress-product-flipbook' ); ?></p>
                <h2><?php esc_html_e( 'Updating your catalogue', 'wordpress-product-flipbook' ); ?></h2>
                <p><?php esc_html_e( 'Rebuild with the same plugin slug and a higher version. Upload the new plugin ZIP and choose to replace the existing plugin. Keep your original source PDF or images outside the plugin directory.', 'wordpress-product-flipbook' ); ?></p>
            </div>
            <?php
        }
    }

    WPCF_Plugin::boot();
} else {
    add_action( 'admin_notices', static function () {
        if ( current_user_can( 'manage_options' ) ) {
            echo '<div class="notice notice-warning"><p>' . esc_html__( 'Two Product Flipbook bundles are active. Keep one active and combine catalogue folders into that bundle to avoid shortcode conflicts.', 'wordpress-product-flipbook' ) . '</p></div>';
        }
    } );
}
