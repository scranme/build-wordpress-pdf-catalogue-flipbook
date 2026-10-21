(function (wp) {
  'use strict';
  if (!wp || !wp.blocks || !wp.element || !wp.blockEditor || !wp.components) return;
  var el = wp.element.createElement;
  var __ = wp.i18n.__;
  var Fragment = wp.element.Fragment;
  wp.blocks.registerBlockType('wpcf/product-flipbook', {
    title: __('Product Flipbook', 'wordpress-product-flipbook'),
    category: 'media',
    icon: 'book-alt',
    attributes: {
      catalogue: { type: 'string', default: 'default' },
      mode: { type: 'string', default: 'overlay' }
    },
    supports: { html: false, multiple: true },
    edit: function (props) {
      var catalogues = Array.isArray(window.WPCFCatalogues) ? window.WPCFCatalogues : [];
      var selected = catalogues.find(function (item) { return item.value === props.attributes.catalogue; });
      var options = catalogues.length ? catalogues : [{ value: 'default', label: __('Default catalogue', 'wordpress-product-flipbook') }];
      var settings = el(wp.components.PanelBody, { title: __('Catalogue settings', 'wordpress-product-flipbook'), initialOpen: true },
        el(wp.components.SelectControl, {
          label: __('Catalogue', 'wordpress-product-flipbook'),
          value: props.attributes.catalogue,
          options: options,
          onChange: function (value) { props.setAttributes({ catalogue: value }); }
        }),
        el(wp.components.SelectControl, {
          label: __('Reader display', 'wordpress-product-flipbook'),
          value: props.attributes.mode,
          options: [
            { label: __('Overlay after opening the cover', 'wordpress-product-flipbook'), value: 'overlay' },
            { label: __('Expand inside the page', 'wordpress-product-flipbook'), value: 'inline' }
          ],
          onChange: function (value) { props.setAttributes({ mode: value }); }
        })
      );
      return el(Fragment, null,
        el(wp.blockEditor.InspectorControls, null, settings),
        el('div', wp.blockEditor.useBlockProps(),
          el(wp.components.Placeholder, { icon: 'book-alt', label: __('Product Flipbook', 'wordpress-product-flipbook') },
            el('p', null, selected ? selected.label + ' · ' + selected.pages + ' pages' : __('Choose a bundled catalogue in the block settings.', 'wordpress-product-flipbook')),
            el('p', null, __('The published page displays a cover. Click it to open the reader. Preview the page to test page turning.', 'wordpress-product-flipbook')),
            el('code', null, '[product_flipbook catalogue="' + props.attributes.catalogue + '" mode="' + props.attributes.mode + '"]')
          )
        )
      );
    },
    save: function () { return null; }
  });
})(window.wp);
