<?php
/**
 * Real WordPress integration checks, for an isolated local test installation.
 * Usage: WPCF_WP_ROOT=/path/to/wordpress php tests/wp-integration-test.php
 * Install and activate a generated plugin containing catalogue "default" first.
 */
if ( 'cli' !== PHP_SAPI ) { exit( 'CLI only.' ); }
$root = getenv( 'WPCF_WP_ROOT' );
if ( ! $root || ! is_file( $root . '/wp-load.php' ) ) {
    fwrite( STDERR, "Set WPCF_WP_ROOT to an isolated WordPress test installation.\n" );
    exit( 2 );
}
$_SERVER['HTTP_HOST'] = getenv( 'WPCF_TEST_HOST' ) ?: '127.0.0.1:8937';
$_SERVER['SERVER_NAME'] = '127.0.0.1';
$_SERVER['REQUEST_URI'] = '/';
$_SERVER['REQUEST_METHOD'] = 'GET';
require $root . '/wp-load.php';
if ( ! in_array( wp_get_environment_type(), array( 'local', 'development' ), true ) ) {
    fwrite( STDERR, "Use a local/development WordPress test installation.\n" );
    exit( 2 );
}

$passed = 0;
function wpcf_assert( $condition, $message ) {
    global $passed;
    if ( ! $condition ) {
        fwrite( STDERR, 'FAIL: ' . $message . PHP_EOL );
        exit( 1 );
    }
    ++$passed;
    echo 'PASS: ' . $message . PHP_EOL;
}

wpcf_assert( class_exists( 'WPCF_Plugin' ), 'Generated plugin activates in real WordPress.' );
wpcf_assert( shortcode_exists( 'product_flipbook' ), 'Shortcode is registered.' );
$block = WP_Block_Type_Registry::get_instance()->get_registered( 'wpcf/product-flipbook' );
wpcf_assert( $block && is_callable( $block->render_callback ), 'Dynamic Gutenberg block is registered.' );
wpcf_assert( in_array( 'wpcf-block-editor', $block->editor_script_handles, true ), 'Gutenberg metadata registers the local editor script.' );
wpcf_assert( ! wp_script_is( 'wpcf-runtime', 'enqueued' ), 'Reader script is not enqueued without a viewer.' );
wpcf_assert( ! wp_style_is( 'wpcf-style', 'enqueued' ), 'Reader CSS is not enqueued without a viewer.' );

$before = count( get_posts( array( 'post_type' => 'page', 'numberposts' => -1 ) ) );
$shortcode = do_shortcode( '[product_flipbook catalogue="default"]' );
wpcf_assert( false !== strpos( $shortcode, 'data-wpcf-open' ), 'Shortcode renders the cover button.' );
wpcf_assert( false !== strpos( $shortcode, 'data-mode="overlay"' ), 'Cover defaults to overlay mode.' );
wpcf_assert( false !== strpos( $shortcode, '<noscript>' ), 'Non-JavaScript fallback is present.' );
wpcf_assert( false !== strpos( $shortcode, 'Browse individual page images' ), 'Page-image fallback links remain available.' );
wpcf_assert( false === strpos( $shortcode, '<iframe' ), 'Reader is integrated without an iframe document.' );
wpcf_assert( wp_script_is( 'wpcf-runtime', 'enqueued' ), 'Shortcode enqueues runtime.' );
wpcf_assert( wp_style_is( 'wpcf-style', 'enqueued' ), 'Shortcode enqueues scoped CSS.' );
$registered = wp_scripts()->registered['wpcf-runtime'];
wpcf_assert( in_array( 'wpcf-page-flip', $registered->deps, true ), 'Page-turn library is an explicit script dependency.' );
foreach ( array( 'wpcf-runtime', 'wpcf-page-flip', 'wpcf-block-editor' ) as $handle ) {
    $src = wp_scripts()->registered[$handle]->src;
    wpcf_assert( 0 === strpos( $src, plugins_url() . '/' ), $handle . ' uses a local plugin URL.' );
}
$catalogues = WPCF_Plugin::catalogue_list();
wpcf_assert( in_array( 'default', array_column( $catalogues, 'value' ), true ), 'Editor catalogue selector includes the built default catalogue.' );
WPCF_Plugin::editor_data();
$editor_data = wp_scripts()->get_data( 'wpcf-block-editor', 'before' );
wpcf_assert( is_array( $editor_data ) && false !== strpos( implode( "\n", $editor_data ), 'window.WPCFCatalogues = ' ), 'Editor receives catalogue data through the WordPress inline-script API.' );

$second = do_shortcode( '[product_flipbook catalogue="default" mode="inline"]' );
preg_match( '/id="(wpcf-[^"]+)"/', $shortcode, $id1 );
preg_match( '/id="(wpcf-[^"]+)"/', $second, $id2 );
wpcf_assert( isset( $id1[1], $id2[1] ) && $id1[1] !== $id2[1], 'Two instances receive distinct IDs.' );
wpcf_assert( false !== strpos( $second, 'data-mode="inline"' ), 'Inline mode is rendered.' );

$block_output = do_blocks( '<!-- wp:wpcf/product-flipbook {"catalogue":"default","mode":"inline"} /-->' );
wpcf_assert( false !== strpos( $block_output, 'data-wpcf-open' ), 'Saved Gutenberg block renders on the frontend.' );
wpcf_assert( false !== strpos( $block_output, 'data-mode="inline"' ), 'Gutenberg mode attribute reaches the renderer.' );

$original_user = get_current_user_id();
wp_set_current_user( 0 );
ob_start();
WPCF_Plugin::admin_page();
wpcf_assert( '' === ob_get_clean(), 'Settings renderer does not disclose data to anonymous visitors.' );
$admins = get_users( array( 'role' => 'administrator', 'number' => 1, 'fields' => 'ID' ) );
wpcf_assert( ! empty( $admins ), 'Local integration site has an administrator for editor checks.' );
wp_set_current_user( $admins[0] );
ob_start();
WPCF_Plugin::admin_page();
$settings = ob_get_clean();
wpcf_assert( false !== strpos( $settings, '[product_flipbook catalogue=&quot;default&quot;]' ), 'Settings screen provides the installed catalogue shortcode.' );
$request = new WP_REST_Request( 'GET', '/wp/v2/block-renderer/wpcf/product-flipbook' );
$request->set_param( 'context', 'edit' );
$request->set_param( 'attributes', array( 'catalogue' => 'default', 'mode' => 'overlay' ) );
$response = rest_do_request( $request );
$rendered = $response->get_data();
wpcf_assert( 200 === $response->get_status() && isset( $rendered['rendered'] ) && false !== strpos( $rendered['rendered'], 'data-wpcf-open' ), 'WordPress REST block renderer returns the dynamic catalogue for an editor.' );
wp_set_current_user( $original_user );

foreach ( array( 'missing-catalogue', '../default', '/etc/passwd', 'https://example.invalid' ) as $invalid ) {
    $result = WPCF_Plugin::render( array( 'catalogue' => $invalid ) );
    wpcf_assert( false !== strpos( $result, 'wpcf-error' ) && false === strpos( $result, 'data-wpcf-open' ), 'Invalid catalogue rejected: ' . $invalid );
    wpcf_assert( false === strpos( $result, ABSPATH ), 'Error does not disclose a filesystem path.' );
}

$after = count( get_posts( array( 'post_type' => 'page', 'numberposts' => -1 ) ) );
wpcf_assert( $before === $after, 'Rendering does not create or publish WordPress pages.' );

// Exercise WordPress's real style printer for late template/widget rendering.
wp_dequeue_style( 'wpcf-style' );
wp_styles()->done = array_values( array_diff( wp_styles()->done, array( 'wpcf-style' ) ) );
$GLOBALS['wp_actions']['wp_head'] = 1;
$late = WPCF_Plugin::render( array( 'catalogue' => 'default' ) );
wpcf_assert( false !== strpos( $late, 'wpcf-style-css' ), 'Late shortcode prints CSS after the head has already run.' );
$later = WPCF_Plugin::render( array( 'catalogue' => 'default' ) );
wpcf_assert( false === strpos( $later, 'wpcf-style-css' ), 'Further late instances do not duplicate the stylesheet.' );
echo "PASS: {$passed} real WordPress integration assertions.\n";
