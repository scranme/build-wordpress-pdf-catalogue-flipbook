<?php
/** Fast contract tests with a narrow WordPress harness. Run: php tests/test_wordpress_plugin.php */
declare(strict_types=1);

define('ABSPATH', __DIR__ . '/');
final class WP_Error {
    private $message;
    public function __construct($code, $message) { $this->message = $message; }
    public function get_error_message() { return $this->message; }
}
class WP_Post { public $post_content = ''; }
$GLOBALS['wpcf_test'] = array('hooks' => array(), 'scripts' => array(), 'styles' => array(), 'enqueued' => array(), 'done' => array(), 'blocks' => array(), 'inline' => array(), 'head' => 1, 'admin' => false, 'capability' => true, 'post' => null);
function add_action($hook, $callback) { $GLOBALS['wpcf_test']['hooks'][$hook][] = $callback; }
function add_shortcode($tag, $callback) { $GLOBALS['wpcf_test']['shortcodes'][$tag] = $callback; }
function register_block_type($directory, $args) { $GLOBALS['wpcf_test']['blocks'][] = array($directory, $args); }
function wp_register_style($handle, $src, $dependencies, $version) { $GLOBALS['wpcf_test']['styles'][$handle] = $src; }
function wp_register_script($handle, $src, $dependencies, $version, $footer) { $GLOBALS['wpcf_test']['scripts'][$handle] = array('src' => $src, 'dependencies' => $dependencies, 'footer' => $footer); }
function plugin_dir_url($file) { return 'https://example.test/wp-content/plugins/catalogue/'; }
function wp_script_is($handle, $status) { return isset($GLOBALS['wpcf_test']['scripts'][$handle]); }
function wp_style_is($handle, $status) { return isset($GLOBALS['wpcf_test']['done'][$handle]); }
function wp_enqueue_style($handle) { $GLOBALS['wpcf_test']['enqueued'][$handle] = true; }
function wp_enqueue_script($handle) { $GLOBALS['wpcf_test']['enqueued'][$handle] = true; }
function wp_print_styles($handles) {
    foreach ($handles as $handle) {
        $GLOBALS['wpcf_test']['done'][$handle] = true;
        echo '<link rel="stylesheet" data-test-style="' . htmlspecialchars($handle) . '">';
    }
}
function is_admin() { return $GLOBALS['wpcf_test']['admin']; }
function get_queried_object() { return $GLOBALS['wpcf_test']['post']; }
function has_shortcode($content, $tag) { return false !== strpos($content, '[' . $tag); }
function has_block($name, $post) { return false !== strpos($post->post_content, '<!-- wp:' . $name); }
function is_wp_error($object) { return $object instanceof WP_Error; }
function shortcode_atts($defaults, $attributes, $tag) { return array_merge($defaults, array_intersect_key($attributes, $defaults)); }
function wp_unique_id($prefix) { static $counter = 0; return $prefix . ++$counter; }
function did_action($hook) { return 'wp_head' === $hook ? $GLOBALS['wpcf_test']['head'] : 0; }
function __($value, $domain = '') { return $value; }
function esc_html__($value, $domain = '') { return esc_html($value); }
function esc_html($value) { return htmlspecialchars((string) $value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }
function esc_attr($value) { return esc_html($value); }
function esc_url($value) { return esc_html($value); }
function esc_html_e($value, $domain = '') { echo esc_html($value); }
function esc_attr_e($value, $domain = '') { echo esc_attr($value); }
function wp_json_encode($value) { return json_encode($value); }
function wp_add_inline_script($handle, $script, $position) { $GLOBALS['wpcf_test']['inline'][$handle] = array($script, $position); }
function add_options_page($page, $menu, $capability, $slug, $callback) { $GLOBALS['wpcf_test']['admin_page'] = $callback; }
function current_user_can($capability) { return $GLOBALS['wpcf_test']['capability']; }

$checks = 0;
function check($condition, $message) {
    global $checks;
    ++$checks;
    if (!$condition) { throw new RuntimeException($message); }
}

$fixture = sys_get_temp_dir() . '/wpcf-contract-' . bin2hex(random_bytes(6));
mkdir($fixture . '/catalogues/default/pages', 0777, true);
mkdir($fixture . '/block', 0777, true);
$template = dirname(__DIR__) . '/assets/wordpress-plugin-template/';
copy($template . 'wordpress-product-flipbook.php', $fixture . '/wordpress-product-flipbook.php');
copy($template . 'block/block.json', $fixture . '/block/block.json');
file_put_contents($fixture . '/catalogues/default/pages/001.webp', 'test fixture');
file_put_contents($fixture . '/catalogues/default/pages/002.webp', 'test fixture');
$manifest = array(
    'schemaVersion' => 1,
    'title' => 'Acme <script>alert(1)</script> & Catalogue',
    'description' => 'Products <strong>and</strong> materials',
    'aspectRatio' => 0.75,
    'pages' => array(
        array('src' => 'pages/001.webp', 'src2x' => 'pages/001.webp', 'thumbnail' => 'pages/001.webp', 'width' => 600, 'height' => 800, 'alt' => 'Cover " quote', 'title' => 'Front'),
        array('src' => 'pages/002.webp', 'thumbnail' => 'pages/002.webp', 'width' => 600, 'height' => 800, 'title' => 'Second'),
    ),
);
file_put_contents($fixture . '/catalogues/default/manifest.json', json_encode($manifest));

// Cleanup is constrained to this newly generated, uniquely named temporary fixture.
register_shutdown_function(static function () use ($fixture) {
    if (0 !== strpos(basename($fixture), 'wpcf-contract-')) { return; }
    $iterator = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($fixture, FilesystemIterator::SKIP_DOTS), RecursiveIteratorIterator::CHILD_FIRST);
    foreach ($iterator as $path) {
        if ($path->isDir()) { rmdir($path->getPathname()); } else { unlink($path->getPathname()); }
    }
    rmdir($fixture);
});

require $fixture . '/wordpress-product-flipbook.php';
WPCF_Plugin::register();
check(isset($GLOBALS['wpcf_test']['shortcodes']['product_flipbook']), 'Shortcode is registered.');
check(1 === count($GLOBALS['wpcf_test']['blocks']), 'Dynamic block is registered.');
check(empty($GLOBALS['wpcf_test']['enqueued']), 'Registering the plugin does not load assets everywhere.');
check(array('wpcf-page-flip') === $GLOBALS['wpcf_test']['scripts']['wpcf-runtime']['dependencies'], 'Runtime depends on the local page-flip library.');
WPCF_Plugin::enqueue_for_content();
check(empty($GLOBALS['wpcf_test']['enqueued']), 'An unrelated page loads no flipbook assets.');

$first = WPCF_Plugin::render();
check(false !== strpos($first, 'data-wpcf-open'), 'A real cover button is rendered.');
check(false !== strpos($first, 'data-manifest="https://example.test/wp-content/plugins/catalogue/catalogues/default/manifest.json?ver=' . rawurlencode(WPCF_Plugin::VERSION) . '"'), 'Manifest URL is a versioned web URL.');
check(false === strpos($first, '<script>alert(1)</script>'), 'Manifest title is escaped.');
check(false !== strpos($first, '&lt;script&gt;'), 'Escaped title remains visible as text.');
check(1 === substr_count($first, '<img '), 'Only the cover is loaded by initial HTML.');
check(2 === substr_count($first, '<li>'), 'No-JavaScript fallback exposes every page.');
check(false !== strpos($first, 'data-test-style="wpcf-style"'), 'A late shortcode prints its stylesheet.');
check(isset($GLOBALS['wpcf_test']['enqueued']['wpcf-runtime']), 'Rendered shortcode enqueues its runtime.');
$second = WPCF_Plugin::render(array('mode' => 'inline'));
preg_match('/id="(wpcf-[^"]+)"/', $first, $first_id);
preg_match('/id="(wpcf-[^"]+)"/', $second, $second_id);
check($first_id[1] !== $second_id[1], 'Multiple readers have unique IDs.');
check(false === strpos($second, 'data-test-style='), 'Stylesheet is not printed twice.');
check(false !== strpos($second, 'data-mode="inline"'), 'Inline mode is preserved.');
check(false !== strpos(WPCF_Plugin::render(array('mode' => 'javascript:evil')), 'data-mode="overlay"'), 'Unrecognized mode uses safe default.');
check(is_wp_error(WPCF_Plugin::catalogue('../default')), 'Traversal slug is rejected.');
check(is_wp_error(WPCF_Plugin::catalogue(array('default'))), 'Non-string slug is rejected.');
check(false !== strpos(WPCF_Plugin::render(array('catalogue' => 'missing')), 'Catalogue not found'), 'Missing catalogue returns useful text.');

foreach (array('external' => 'https://evil.test/page.webp', 'traversal' => '../default/pages/001.webp', 'encoded' => 'pages/%2e%2e/001.webp', 'backslash' => 'pages\\001.webp') as $slug => $src) {
    mkdir($fixture . '/catalogues/' . $slug, 0777, true);
    $bad = $manifest;
    $bad['pages'][0]['src'] = $src;
    file_put_contents($fixture . '/catalogues/' . $slug . '/manifest.json', json_encode($bad));
    check(is_wp_error(WPCF_Plugin::catalogue($slug)), 'Unsafe path is rejected: ' . $slug);
}
mkdir($fixture . '/catalogues/keyed');
$bad = $manifest;
$bad['pages'] = array('first' => $manifest['pages'][0]);
file_put_contents($fixture . '/catalogues/keyed/manifest.json', json_encode($bad));
check(is_wp_error(WPCF_Plugin::catalogue('keyed')), 'A non-list page collection is rejected.');
check(1 === count(WPCF_Plugin::catalogue_list()), 'Only valid catalogues reach the admin list.');
WPCF_Plugin::editor_data();
check(isset($GLOBALS['wpcf_test']['inline']['wpcf-block-editor']), 'Block editor gets bundled catalogue choices.');
$GLOBALS['wpcf_test']['capability'] = false;
ob_start();
WPCF_Plugin::admin_page();
$admin_output = ob_get_clean();
check('' === $admin_output, 'Settings content requires manage_options.');
$GLOBALS['wpcf_test']['capability'] = true;
ob_start();
WPCF_Plugin::admin_page();
$admin_output = ob_get_clean();
check(false !== strpos($admin_output, 'product_flipbook catalogue='), 'Admin page provides copyable shortcodes.');
check(false === strpos($admin_output, '<script>alert(1)</script>'), 'Admin table escapes catalogue titles.');

echo "PASS: {$checks} WordPress plugin contract checks.\n";
