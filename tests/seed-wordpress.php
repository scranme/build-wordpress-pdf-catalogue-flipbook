<?php
/**
 * Seed browser-smoke.cjs pages in a disposable local WordPress installation.
 *
 * Usage: WPCF_WP_ROOT=/path/to/wordpress php tests/seed-wordpress.php
 * Optional: WPCF_TEST_HOST=localhost:8080 for a host-sensitive local setup.
 * Install and activate a generated plugin containing catalogue "default" first.
 * This script does not install WordPress, change themes/permalinks, or set users.
 * Existing pages may be updated only when this script's ownership marker matches.
 */
if ( 'cli' !== PHP_SAPI ) {
    exit( 'CLI only.' );
}

function wpcf_seed_fail( $message ) {
    fwrite( STDERR, 'ERROR: ' . $message . PHP_EOL );
    exit( 2 );
}

$requested_root = getenv( 'WPCF_WP_ROOT' );
$root = $requested_root ? realpath( $requested_root ) : false;
if ( ! $root || ! is_file( $root . '/wp-load.php' ) ) {
    wpcf_seed_fail( 'Set WPCF_WP_ROOT to a disposable local WordPress installation.' );
}
$test_host = getenv( 'WPCF_TEST_HOST' ) ?: 'localhost';
if ( preg_match( '/[\x00-\x20\/\\\\]/', $test_host ) ) {
    wpcf_seed_fail( 'WPCF_TEST_HOST must be a host, optionally followed by a port.' );
}
$_SERVER['HTTP_HOST'] = $test_host;
$_SERVER['SERVER_NAME'] = parse_url( 'http://' . $test_host, PHP_URL_HOST ) ?: 'localhost';
$_SERVER['REQUEST_URI'] = '/';
$_SERVER['REQUEST_METHOD'] = 'GET';
require $root . '/wp-load.php';

if ( ! in_array( wp_get_environment_type(), array( 'local', 'development' ), true ) ) {
    wpcf_seed_fail( 'Refusing to seed a site outside the local/development environment.' );
}
if ( ! class_exists( 'WPCF_Plugin', false ) || ! shortcode_exists( 'product_flipbook' ) ) {
    wpcf_seed_fail( 'Activate a generated Product Flipbook plugin before seeding fixtures.' );
}
if ( is_wp_error( WPCF_Plugin::catalogue( 'default' ) ) ) {
    wpcf_seed_fail( 'The active plugin needs a valid default catalogue.' );
}

$marker_key = '_wpcf_test_fixture';
$marker_value = 'wordpress-product-flipbook/browser-smoke/v1';
$fixtures = array(
    'catalogue-demo' => array( 'Catalogue demo', '[product_flipbook catalogue="default"]' ),
    'catalogue-inline' => array( 'Inline catalogue', '[product_flipbook catalogue="default" mode="inline"]' ),
    'catalogue-multiple' => array( 'Multiple catalogues', '[product_flipbook catalogue="default"]' . "\n" . '[product_flipbook catalogue="default" mode="inline"]' ),
    'catalogue-block' => array( 'Gutenberg catalogue', '<!-- wp:wpcf/product-flipbook {"catalogue":"default","mode":"overlay"} /-->' ),
    'ordinary-page' => array( 'Ordinary page', '<!-- wp:paragraph --><p>This page contains no catalogue.</p><!-- /wp:paragraph -->' ),
    'catalogue-missing' => array( 'Unavailable catalogue', '[product_flipbook catalogue="missing"]' ),
);

// Preflight every slug before changing anything, including drafts and other types.
$owned_ids = array();
foreach ( $fixtures as $slug => $fixture ) {
    $matches = get_posts( array(
        'name' => $slug,
        'post_type' => array_values( get_post_types() ),
        'post_status' => array_values( get_post_stati() ),
        'numberposts' => -1,
        'suppress_filters' => true,
    ) );
    if ( count( $matches ) > 1 ) {
        wpcf_seed_fail( 'Conflicting content already uses fixture slug "' . $slug . '". No fixture pages were changed.' );
    }
    $existing = $matches ? $matches[0] : null;
    if ( $existing && (
        'page' !== $existing->post_type || 0 !== (int) $existing->post_parent ||
        $marker_value !== get_post_meta( $existing->ID, $marker_key, true )
    ) ) {
        wpcf_seed_fail( 'Refusing to overwrite unowned content at "' . $slug . '". No fixture pages were changed.' );
    }
    $owned_ids[ $slug ] = $existing ? (int) $existing->ID : 0;
}

foreach ( $fixtures as $slug => $fixture ) {
    $id = wp_insert_post( array(
        'ID' => $owned_ids[ $slug ],
        'post_type' => 'page',
        'post_status' => 'publish',
        'post_title' => $fixture[0],
        'post_name' => $slug,
        'post_content' => $fixture[1],
        'post_parent' => 0,
        'meta_input' => array( $marker_key => $marker_value ),
    ), true );
    if ( is_wp_error( $id ) ) {
        wpcf_seed_fail( 'Could not save fixture "' . $slug . '": ' . $id->get_error_message() );
    }
    if ( $slug !== get_post_field( 'post_name', $id ) || $marker_value !== get_post_meta( $id, $marker_key, true ) ) {
        wpcf_seed_fail( 'Fixture slug or marker could not be confirmed for "' . $slug . '".' );
    }
    echo ( $owned_ids[ $slug ] ? 'Updated: ' : 'Created: ' ) . get_permalink( $id ) . PHP_EOL;
}
echo 'Seeded 6 owned fixture pages. Theme and permalink settings were left unchanged.' . PHP_EOL;
