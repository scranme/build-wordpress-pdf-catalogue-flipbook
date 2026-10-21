/* WordPress PDF Catalogue Flipbook · MIT · independent WordPress integration runtime. */
(function () {
  'use strict';
  const instances = new WeakMap();
  let sequence = 0;
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  function safeURL(value, base, local) {
    if (typeof value !== 'string' || !value.trim()) return null;
    try {
      const url = new URL(value, base);
      if (!['http:', 'https:'].includes(url.protocol)) return null;
      if (local && url.origin !== new URL(base).origin) return null;
      if (local) {
        const version = new URL(base).searchParams.get('ver');
        if (version) url.searchParams.set('ver', version);
      }
      return url.href;
    } catch (_) { return null; }
  }
  function validate(data, base) {
    if (!data || data.schemaVersion !== 1 || !Array.isArray(data.pages) || !data.pages.length) {
      throw new Error('The catalogue manifest is incomplete.');
    }
    const ratio = Number(data.aspectRatio);
    if (!Number.isFinite(ratio) || ratio < 0.1 || ratio > 5) throw new Error('Invalid page dimensions.');
    data.pages.forEach((page) => {
      ['src', 'thumbnail'].forEach((key) => {
        page[key] = safeURL(page[key], base, true);
        if (!page[key]) throw new Error('A catalogue image has an invalid address.');
      });
      page.src2x = safeURL(page.src2x, base, true) || page.src;
      page.links = Array.isArray(page.links) ? page.links.filter((link) => {
        link.url = safeURL(link.url, window.location.href, false);
        return link.url && [link.x, link.y, link.width, link.height].every(Number.isFinite)
          && link.x >= 0 && link.y >= 0 && link.width > 0 && link.height > 0
          && link.x + link.width <= 100 && link.y + link.height <= 100;
      }) : [];
    });
    return data;
  }
  class Reader {
    constructor(root) {
      this.root = root;
      this.trigger = root.querySelector('[data-wpcf-open]');
      if (!this.trigger) return;
      this.inline = root.dataset.mode === 'inline';
      this.current = 0;
      this.selected = 0;
      this.loadToken = 0;
      this.busy = false;
      this.opened = false;
      this.trigger.addEventListener('click', () => this.open());
    }
    button(label, action, cls) {
      const node = el('button', 'wpcf-button ' + (cls || ''), label);
      node.type = 'button';
      node.addEventListener('click', action);
      return node;
    }
    createUI() {
      const id = 'wpcf-reader-' + (++sequence);
      this.panel = el(this.inline ? 'section' : 'dialog', 'wpcf-reader');
      this.panel.dataset.mode = this.inline ? 'inline' : 'overlay';
      this.panel.setAttribute('aria-labelledby', id);
      if (this.inline) this.panel.setAttribute('role', 'region');
      const heading = el('div', 'wpcf-heading');
      const title = el('h2', 'wpcf-title', this.root.dataset.title || 'Product catalogue');
      title.id = id;
      this.closeButton = this.button('Back to cover', () => this.close(), 'wpcf-close');
      heading.append(title, this.closeButton);
      this.toolbar = el('div', 'wpcf-toolbar');
      this.toolbar.setAttribute('role', 'group');
      this.toolbar.setAttribute('aria-label', 'Catalogue controls');
      this.prev = this.button('← Previous', () => this.turn(-1));
      this.next = this.button('Next →', () => this.turn(1));
      this.pagesButton = this.button('Pages', () => this.togglePages());
      this.pagesButton.setAttribute('aria-expanded', 'false');
      this.zoomButton = this.button('Zoom', () => this.toggleZoom());
      this.zoomButton.setAttribute('aria-pressed', 'false');
      this.fullButton = this.button('Fullscreen', () => this.fullscreen());
      // Native dialogs cannot be Fullscreen API targets; their top layer remains
      // visible when the document element enters fullscreen.
      this.fullscreenTarget = this.inline ? this.panel : document.documentElement;
      if (!this.fullscreenTarget.requestFullscreen) this.fullButton.hidden = true;
      document.addEventListener('fullscreenchange', () => {
        const active = document.fullscreenElement === this.fullscreenTarget && this.ownsFullscreen;
        this.fullButton.textContent = active ? 'Exit fullscreen' : 'Fullscreen';
        this.fullButton.setAttribute('aria-pressed', String(Boolean(active)));
        if (!document.fullscreenElement) this.ownsFullscreen = false;
      });
      const jumpLabel = el('label', 'wpcf-jump', 'Page ');
      this.jump = el('input');
      this.jump.type = 'number'; this.jump.min = '1'; this.jump.value = '1'; this.jump.inputMode = 'numeric';
      this.jump.setAttribute('aria-label', 'Page number');
      this.jump.addEventListener('change', () => this.go(Number(this.jump.value) - 1));
      this.jump.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') this.go(Number(this.jump.value) - 1);
      });
      jumpLabel.append(this.jump);
      this.counter = el('span', 'wpcf-counter', '');
      this.counter.setAttribute('aria-live', 'polite');
      this.toolbar.append(this.prev, this.next, jumpLabel, this.counter, this.pagesButton, this.zoomButton, this.fullButton);
      this.searchForm = el('form', 'wpcf-search');
      this.searchForm.setAttribute('role', 'search');
      this.searchForm.setAttribute('aria-label', 'Search catalogue pages');
      this.search = el('input'); this.search.type = 'search'; this.search.placeholder = 'Search product / SKU / page';
      this.search.setAttribute('aria-label', 'Search product, SKU, or page');
      const searchButton = el('button', 'wpcf-button', 'Search'); searchButton.type = 'submit';
      this.searchForm.append(this.search, searchButton);
      this.searchForm.addEventListener('submit', (event) => { event.preventDefault(); this.showResults(); });
      this.results = el('div', 'wpcf-results'); this.results.hidden = true;
      this.results.setAttribute('aria-live', 'polite');
      this.thumbs = el('div', 'wpcf-thumbs'); this.thumbs.id = id + '-pages'; this.thumbs.hidden = true;
      this.pagesButton.setAttribute('aria-controls', this.thumbs.id);
      this.stage = el('div', 'wpcf-stage');
      this.status = el('div', 'wpcf-status', 'Loading catalogue…'); this.status.setAttribute('role', 'status');
      this.host = el('div', 'wpcf-book-host');
      this.zoomPane = el('div', 'wpcf-zoom'); this.zoomPane.hidden = true;
      this.zoomTools = el('div', 'wpcf-zoom-tools');
      this.zoomPrevious = this.button('← Page', () => this.zoomPage(-1));
      this.zoomNext = this.button('Page →', () => this.zoomPage(1));
      this.zoomTools.append(this.zoomPrevious, this.zoomNext);
      const zoomOut = this.button('−', () => this.scaleZoom(-0.5));
      const zoomIn = this.button('+', () => this.scaleZoom(0.5));
      zoomOut.setAttribute('aria-label', 'Zoom out');
      zoomIn.setAttribute('aria-label', 'Zoom in');
      this.zoomTools.append(zoomOut, zoomIn);
      this.zoomTools.append(this.button('Return to book', () => this.toggleZoom(false)));
      this.zoomScroll = el('div', 'wpcf-zoom-scroll');
      this.zoomImage = el('img'); this.zoomScroll.append(this.zoomImage);
      this.zoomLinks = el('div', 'wpcf-zoom-links');
      this.zoomPane.append(this.zoomTools, this.zoomScroll, this.zoomLinks);
      this.stage.append(this.status, this.host, this.zoomPane);
      this.panel.append(heading, this.toolbar, this.searchForm, this.results, this.thumbs, this.stage);
      this.panel.addEventListener('cancel', (event) => { event.preventDefault(); this.close(); });
      this.panel.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') { event.preventDefault(); this.close(); return; }
        if (event.target.closest('input,textarea,select,a')) return;
        if (event.key === 'ArrowRight') { event.preventDefault(); this.turn(1); }
        if (event.key === 'ArrowLeft') { event.preventDefault(); this.turn(-1); }
      });
      (this.inline ? this.root : document.body).append(this.panel);
      this.observer = new ResizeObserver(() => {
        if (!this.opened || !this.data) return;
        clearTimeout(this.resizeTimer);
        this.resizeTimer = setTimeout(() => this.mount(), 120);
      });
      this.observer.observe(this.stage);
    }
    async open() {
      if (this.opened) return;
      if (!this.panel) this.createUI();
      this.opened = true;
      if (this.inline) { this.panel.hidden = false; this.trigger.hidden = true; }
      else this.panel.showModal();
      this.closeButton.focus();
      if (this.data) { this.mount(true); return; }
      await this.load();
    }
    async load() {
      if (this.loadController) this.loadController.abort();
      const token = ++this.loadToken;
      this.toolbar.hidden = true; this.searchForm.hidden = true;
      this.status.hidden = false; this.status.replaceChildren(document.createTextNode('Loading catalogue…'));
      const controller = new AbortController();
      this.loadController = controller;
      const timeout = setTimeout(() => controller.abort(), 15000);
      try {
        const base = safeURL(this.root.dataset.manifest, window.location.href, true);
        if (!base) throw new Error('Invalid catalogue address.');
        const response = await fetch(base, { signal: controller.signal, credentials: 'same-origin' });
        if (!response.ok) throw new Error('Catalogue request failed (' + response.status + ').');
        const data = validate(await response.json(), base);
        if (token !== this.loadToken) return;
        this.data = data;
        if (!window.St || !window.St.PageFlip) throw new Error('The local page-turn library did not load.');
        this.jump.max = String(this.data.pages.length);
        this.toolbar.hidden = false; this.searchForm.hidden = false;
        if (this.opened) this.mount(true);
      } catch (error) {
        if (token !== this.loadToken) return;
        this.data = null;
        this.status.replaceChildren(el('p', '', 'The catalogue could not be opened. Please retry.'));
        const details = el('small', '', error.name === 'AbortError' ? 'The request timed out.' : error.message);
        this.status.append(details, this.button('Retry', () => this.load()));
      } finally {
        clearTimeout(timeout);
        if (this.loadController === controller) this.loadController = null;
      }
    }
    mount(force) {
      if (!this.opened || !this.data || !window.St) return;
      const bounds = this.stage.getBoundingClientRect();
      if (bounds.width < 60 || bounds.height < 60) return;
      const single = bounds.width < 740;
      const width = Math.max(20, Math.floor(Math.min((bounds.width - 32) / (single ? 1 : 2), (bounds.height - 24) * this.data.aspectRatio)));
      const height = Math.round(width / this.data.aspectRatio);
      const key = [width, height, single].join(':');
      if (!force && key === this.sizeKey) return;
      this.sizeKey = key;
      const selected = this.selected;
      this.toggleZoom(false);
      if (this.engine) { this.engine.destroy(); this.engine = null; }
      this.host.replaceChildren();
      const book = el('div', 'wpcf-book');
      // The available width determines whether StPageFlip uses portrait mode.
      this.host.style.width = (single ? width : width * 2) + 'px';
      this.host.style.height = height + 'px';
      this.pages = this.data.pages.map((page, index) => {
        const leaf = el('div', 'wpcf-page');
        leaf.setAttribute('aria-label', page.title || 'Page ' + (index + 1));
        if (index === 0 || index === this.data.pages.length - 1) leaf.dataset.density = 'hard';
        const image = el('img', 'wpcf-page-image');
        image.alt = page.alt || page.title || 'Catalogue page ' + (index + 1);
        image.width = page.width; image.height = page.height; image.decoding = 'async'; image.draggable = false;
        image.addEventListener('error', () => {
          if (!image.getAttribute('src')) return;
          leaf.classList.add('wpcf-image-error');
        });
        image.addEventListener('load', () => leaf.classList.remove('wpcf-image-error'));
        const fallback = el('span', 'wpcf-image-message', 'Page image unavailable. Close and reopen to retry.');
        leaf.append(image, fallback);
        page.links.forEach((link) => {
          const anchor = el('a', 'wpcf-hotspot'); anchor.href = link.url;
          anchor.setAttribute('aria-label', link.label || 'View product'); anchor.title = link.label || 'View product';
          anchor.style.left = link.x + '%'; anchor.style.top = link.y + '%';
          anchor.style.width = link.width + '%'; anchor.style.height = link.height + '%';
          leaf.append(anchor);
        });
        book.append(leaf);
        return { leaf, image };
      });
      this.host.append(book);
      this.engine = new window.St.PageFlip(book, {
        width, height, size: 'fixed', autoSize: false, usePortrait: true,
        showCover: true, startPage: Math.min(selected, this.pages.length - 1),
        drawShadow: true, maxShadowOpacity: 0.22,
        flippingTime: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 1 : 550,
        mobileScrollSupport: true, useMouseEvents: true, clickEventForward: true,
        showPageCorners: true, disableFlipByClick: false
      });
      this.busy = false;
      this.engine.on('flip', (event) => { this.current = event.data; this.selected = this.current; this.refresh(); });
      this.engine.on('changeState', (event) => { this.busy = event.data === 'flipping'; this.updateButtons(); });
      this.engine.loadFromHTML(this.pages.map((page) => page.leaf));
      this.selected = selected;
      this.status.hidden = true;
      this.refresh();
    }
    updateButtons() {
      this.prev.disabled = this.busy || this.current <= 0;
      this.next.disabled = this.busy || !this.data || this.lastVisiblePage() >= this.data.pages.length - 1;
      this.jump.disabled = this.busy;
    }
    lastVisiblePage() {
      return this.current + (this.engine && this.engine.getOrientation() === 'landscape' && this.current > 0 ? 1 : 0);
    }
    refresh() {
      const count = this.data.pages.length;
      this.jump.value = String(this.selected + 1);
      this.counter.textContent = '/ ' + count;
      this.panel.dataset.page = String(this.selected + 1);
      this.panel.dataset.spreadStart = String(this.current + 1);
      this.panel.dataset.orientation = this.engine.getOrientation();
      this.updateButtons();
      this.pages.forEach(({ image, leaf }, index) => {
        const page = this.data.pages[index];
        const visible = index >= this.current && index <= this.lastVisiblePage();
        leaf.setAttribute('aria-hidden', String(!visible));
        leaf.querySelectorAll('a').forEach((anchor) => { anchor.tabIndex = visible ? 0 : -1; });
        if (Math.abs(index - this.current) <= 3) {
          if (!image.getAttribute('src')) {
            // Width descriptors preserve quality without downloading high-res pages twice.
            image.sizes = Math.round(this.host.clientWidth / (this.engine.getOrientation() === 'portrait' ? 1 : 2)) + 'px';
            if (page.src2x !== page.src) image.srcset = page.src + ' ' + page.width + 'w, ' + page.src2x + ' ' + (page.retinaWidth || Math.round(page.width * 1.5)) + 'w';
            image.src = page.src;
          }
        } else if (Math.abs(index - this.current) > 6) {
          image.removeAttribute('srcset'); image.removeAttribute('src');
        }
      });
      if (this.thumbButtons) this.thumbButtons.forEach((button, i) => button.setAttribute('aria-current', i === this.selected ? 'page' : 'false'));
    }
    turn(direction) {
      if (!this.engine || this.busy) return;
      this.toggleZoom(false);
      if (direction > 0 && this.lastVisiblePage() < this.data.pages.length - 1) this.engine.flipNext();
      else if (direction < 0 && this.current > 0) this.engine.flipPrev();
    }
    go(index) {
      if (!this.engine || this.busy || !Number.isFinite(index)) return;
      this.toggleZoom(false);
      const selected = Math.max(0, Math.min(this.data.pages.length - 1, Math.floor(index)));
      this.engine.turnToPage(selected);
      this.selected = selected;
      this.current = this.engine.getCurrentPageIndex(); this.refresh();
    }
    togglePages() {
      if (!this.data) return;
      if (!this.thumbButtons) this.thumbButtons = this.data.pages.map((page, i) => {
        const button = this.button('', () => { this.go(i); this.togglePages(); });
        button.setAttribute('aria-label', 'Open page ' + (i + 1) + ': ' + (page.title || ''));
        const image = el('img'); image.src = page.thumbnail; image.loading = 'lazy'; image.alt = '';
        image.width = page.width; image.height = page.height;
        button.append(image, el('span', '', String(i + 1))); this.thumbs.append(button); return button;
      });
      this.thumbs.hidden = !this.thumbs.hidden;
      this.pagesButton.setAttribute('aria-expanded', String(!this.thumbs.hidden));
      this.refresh();
    }
    showResults() {
      if (!this.data) return;
      const query = this.search.value.trim().toLocaleLowerCase();
      this.results.replaceChildren(); this.results.hidden = !query;
      if (!query) return;
      const found = [];
      this.data.pages.forEach((page, i) => {
        const haystack = [page.title, page.text, page.alt, String(i + 1)].join(' ').toLocaleLowerCase();
        if (haystack.includes(query)) found.push({ page, i });
      });
      this.results.append(el('span', '', found.length ? found.length + ' matching pages' : 'No matching pages. Scanned pages need searchable metadata.'));
      found.slice(0, 60).forEach(({ page, i }) => this.results.append(this.button((i + 1) + ' · ' + (page.title || 'Page'), () => {
        this.go(i); this.results.hidden = true;
      })));
    }
    toggleZoom(value) {
      if (!this.data || !this.zoomPane) return;
      const show = value === undefined ? this.zoomPane.hidden : value;
      this.zoomPane.hidden = !show;
      this.zoomButton.setAttribute('aria-pressed', String(show));
      if (show) {
        const page = this.data.pages[this.selected];
        this.zoomPrevious.disabled = this.selected <= 0;
        this.zoomNext.disabled = this.selected >= this.data.pages.length - 1;
        this.zoomImage.src = page.src2x; this.zoomImage.alt = page.alt || page.title || 'Catalogue page';
        this.zoomScale = 1.5; this.scaleZoom(0);
        this.zoomLinks.replaceChildren();
        page.links.forEach((link) => { const anchor = el('a', 'wpcf-button', link.label || 'View product'); anchor.href = link.url; this.zoomLinks.append(anchor); });
      } else if (this.zoomImage) this.zoomImage.removeAttribute('src');
    }
    zoomPage(delta) {
      this.go(this.selected + delta);
      this.toggleZoom(true);
    }
    scaleZoom(delta) {
      this.zoomScale = Math.min(4, Math.max(1, this.zoomScale + delta));
      this.zoomImage.style.width = Math.round(Math.max(120, this.zoomScroll.clientHeight - 16) * this.data.aspectRatio * this.zoomScale) + 'px';
    }
    async fullscreen() {
      try {
        if (document.fullscreenElement === this.fullscreenTarget && this.ownsFullscreen) await document.exitFullscreen();
        else if (this.fullscreenTarget.requestFullscreen) {
          this.ownsFullscreen = true;
          await this.fullscreenTarget.requestFullscreen();
        }
      } catch (_) { this.ownsFullscreen = false; this.fullButton.textContent = 'Fullscreen unavailable'; }
    }
    close() {
      if (!this.opened) return;
      this.loadToken += 1;
      if (this.loadController) this.loadController.abort();
      this.opened = false; clearTimeout(this.resizeTimer);
      if (document.fullscreenElement === this.fullscreenTarget && this.ownsFullscreen) document.exitFullscreen().catch(() => {});
      this.toggleZoom(false);
      if (this.engine) { this.engine.destroy(); this.engine = null; }
      this.sizeKey = null;
      if (this.inline) { this.panel.hidden = true; this.trigger.hidden = false; }
      else this.panel.close();
      this.trigger.focus();
    }
  }
  function init() {
    document.querySelectorAll('[data-wpcf]').forEach((root) => {
      if (!instances.has(root)) { instances.set(root, new Reader(root)); }
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
  // Page builders can call this after inserting shortcode markup dynamically.
  window.WPCatalogueFlipbook = { init };
})();
