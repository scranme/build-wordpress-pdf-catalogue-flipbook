#!/usr/bin/env node
/** Deterministic lifecycle-only patch for the MIT-licensed StPageFlip 2.0.7 bundle. */
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const ORIGINAL_SHA256 = 'bbaca0bbef57a22bb66a3fc69d67baf9a17fb9a9c89ec9ed35e2b91abe4bd1e7';
export const PATCHED_SHA256 = '09c07732ff868f0c3c3792df0eeb46b414a98a32a9f976fad4a2d75aad6af220';
const DEFAULT_VENDOR = fileURLToPath(new URL('../assets/wordpress-plugin-template/assets/vendor/page-flip.browser.js', import.meta.url));

const replacements = [
  [
    'start(){this.update();const t=e=>{this.render(e),requestAnimationFrame(t)};requestAnimationFrame(t)}startAnimation',
    'start(){this.stop(),this.update(),this.wpcfRunning=!0;const t=e=>{this.wpcfRunning&&(this.render(e),this.wpcfRunning&&(this.wpcfFrame=requestAnimationFrame(t)))};this.wpcfFrame=requestAnimationFrame(t)}stop(){this.wpcfRunning=!1,void 0!==this.wpcfFrame&&(cancelAnimationFrame(this.wpcfFrame),this.wpcfFrame=void 0),this.animation=null}startAnimation',
  ],
  [
    'destroy(){this.ui.destroy(),this.block.remove()}update()',
    'destroy(){this.render&&this.render.stop(),this.ui&&this.ui.destroy(),this.block.remove()}update()',
  ],
];

export function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

export function patchVendor(bytes) {
  const hash = sha256(bytes);
  if (hash === PATCHED_SHA256) return bytes;
  if (hash !== ORIGINAL_SHA256) throw new Error('Refusing to patch an unknown vendor file: SHA-256 ' + hash);
  let source = bytes.toString('utf8');
  for (const [before, after] of replacements) {
    if (source.split(before).length !== 2) throw new Error('Vendor patch anchor must occur exactly once: ' + before);
    source = source.replace(before, after);
  }
  const result = Buffer.from(source, 'utf8');
  if (sha256(result) !== PATCHED_SHA256) throw new Error('Patched vendor checksum mismatch: ' + sha256(result));
  return result;
}

function main() {
  const args = process.argv.slice(2);
  const checkOnly = args[0] === '--check';
  const pathArg = checkOnly ? args[1] : args[0];
  if (args.length > (checkOnly ? 2 : 1) || (pathArg && pathArg.startsWith('--'))) {
    throw new Error('Usage: node scripts/patch_vendor.mjs [--check] [path/to/page-flip.browser.js]');
  }
  const path = pathArg ? resolve(pathArg) : DEFAULT_VENDOR;
  const original = readFileSync(path);
  if (checkOnly) {
    if (sha256(original) !== PATCHED_SHA256) throw new Error('Vendor file is not the pinned lifecycle-patched bundle.');
    console.log('PASS: pinned StPageFlip lifecycle patch checksum.');
    return;
  }
  const patched = patchVendor(original);
  if (patched !== original) writeFileSync(path, patched);
  console.log((patched === original ? 'Already patched: ' : 'Patched: ') + path);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { main(); } catch (error) { console.error(error.message); process.exitCode = 1; }
}
