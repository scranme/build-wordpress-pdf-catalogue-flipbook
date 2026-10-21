/** Lifecycle regression tests execute the actual bundled Render and PageFlip classes. */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { PATCHED_SHA256, patchVendor, sha256 } from '../scripts/patch_vendor.mjs';

const bytes = readFileSync(new URL('../assets/wordpress-plugin-template/assets/vendor/page-flip.browser.js', import.meta.url));
assert.equal(sha256(bytes), PATCHED_SHA256, 'The test uses the pinned patched vendor bundle.');
assert.equal(patchVendor(bytes), bytes, 'The patch is idempotent.');
assert.throws(() => patchVendor(Buffer.from('unknown upstream code')), /unknown vendor file/, 'Unknown upstream code must not be rewritten.');

// Expose the otherwise private renderer in memory only. The distributed file is unchanged.
const source = bytes.toString('utf8');
const anchor = 't.PageFlip=class extends class{';
assert.equal(source.split(anchor).length, 2, 'The pinned bundle has exactly one export anchor.');
const testSource = source.replace(anchor, 't.__TestRender=l;' + anchor);
let nextId = 1;
const pending = new Map();
const context = {
  exports: {}, module: {},
  window: { navigator: { userAgent: 'LifecycleRegression' } },
  requestAnimationFrame(callback) { const id = nextId++; pending.set(id, callback); return id; },
  cancelAnimationFrame(id) { pending.delete(id); },
};
vm.runInNewContext(testSource, context, { filename: 'page-flip.browser.js' });
const { __TestRender: Render, PageFlip } = context.exports;
let draws = 0;
function renderer() {
  const result = new Render({}, {});
  result.update = () => {};
  result.drawFrame = () => { draws++; };
  return result;
}
function frame() {
  const callbacks = [...pending.entries()];
  pending.clear();
  callbacks.forEach(([, callback]) => callback(16));
}

const first = renderer();
first.start();
assert.equal(pending.size, 1, 'Starting schedules one frame.');
frame();
assert.equal(draws, 1, 'An active reader renders.');
assert.equal(pending.size, 1, 'An active reader keeps one, not multiple, pending frames.');
const staleCallback = [...pending.values()][0];
first.animation = { frames: [() => {}] };
first.stop();
assert.equal(pending.size, 0, 'Stopping cancels the pending frame.');
assert.equal(first.animation, null, 'Stopping releases the pending animation.');
first.stop();
staleCallback(32);
assert.equal(draws, 1, 'Even a late delivered callback cannot draw after stop.');
assert.equal(pending.size, 0, 'A late callback cannot restart the loop.');

first.start();
first.start();
assert.equal(pending.size, 1, 'Repeated starts do not accumulate frame loops.');
first.stop();
for (let i = 0; i < 50; i++) {
  const render = renderer();
  const book = new PageFlip({ remove() {} }, { width: 600, height: 800 });
  book.render = render;
  book.ui = { destroy() { assert.equal(pending.size, 0, 'Destroy stops rendering before removing UI.'); } };
  render.start();
  book.destroy();
}
assert.equal(pending.size, 0, 'Repeated mount/destroy leaves no live frame loops.');

const stopDuringDraw = renderer();
stopDuringDraw.drawFrame = () => stopDuringDraw.stop();
stopDuringDraw.start();
frame();
assert.equal(pending.size, 0, 'Destroy during render does not schedule another frame.');

const left = renderer();
const right = renderer();
left.start(); right.start();
assert.equal(pending.size, 2, 'Separate readers have separate loops.');
left.stop();
assert.equal(pending.size, 1, 'Stopping one reader does not cancel the other.');
right.stop();
assert.equal(pending.size, 0);
console.log('PASS: StPageFlip lifecycle cleanup, repeated teardown, late callbacks, independent readers and pinned patch checks.');
