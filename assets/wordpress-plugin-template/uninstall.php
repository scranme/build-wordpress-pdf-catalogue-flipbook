<?php
/** The read-only plugin creates no options, posts, uploads or database tables. */
if ( ! defined( 'WP_UNINSTALL_PLUGIN' ) ) {
    exit;
}
// WordPress removes bundled assets with the plugin. No site content is deleted here.
