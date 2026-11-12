'use strict';

/**
 * Node-run contract test for the Rules YAML editor layout (ticket 122,
 * issue #138): the displayed zone (pre.yaml-highlight) and the editable
 * zone (textarea.yaml-editor) must share one fixed-height box, or the
 * highlight shows lines the textarea's scrollbar cannot reach.
 *
 * The panel has no build toolchain, so this pins the CSS contract by
 * reading RULES_STYLES out of regles.js directly (same approach as the
 * coherence style pins).
 *
 * Run: node tests/js/test-regles-styles.js (exit 0 on success)
 */

const fs = require('fs');
const path = require('path');

const REGLES_PATH = path.resolve(
  __dirname,
  '..',
  '..',
  'custom_components',
  'eedomus',
  'www',
  'panel',
  'regles.js'
);

let failures = 0;

function check(name, cond) {
  if (cond) {
    console.log(`PASS  ${name}`);
  } else {
    failures += 1;
    console.log(`FAIL  ${name}`);
  }
}

function ruleBlock(css, selector) {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const m = css.match(new RegExp(esc + '\\s*\\{([^}]*)\\}'));
  return m ? m[1] : null;
}

const src = fs.readFileSync(REGLES_PATH, 'utf8');
const stylesMatch = src.match(/RULES_STYLES\s*=\s*`([\s\S]*?)`/);
check('RULES_STYLES template found in regles.js', Boolean(stylesMatch));
const css = stylesMatch ? stylesMatch[1] : '';

// One shared fixed-height box for display + edit (ticket 122).
const wrap = ruleBlock(css, '.yaml-editor-wrap');
check('wrap has a fixed height (height: 420px)', !!wrap && /height:\s*420px/.test(wrap));
check('wrap keeps overflow: hidden (clips the overlay)', !!wrap && /overflow:\s*hidden/.test(wrap));
check('wrap keeps the vertical resize affordance', !!wrap && /resize:\s*vertical/.test(wrap));

const editor = ruleBlock(css, '.yaml-editor');
check('textarea fills the shared box (height: 100%)', !!editor && /height:\s*100%/.test(editor));
check('textarea min-height removed (no second box)', !!editor && !/min-height:\s*420px/.test(editor));
check('textarea cannot be resized independently (resize: none)', !!editor && /resize:\s*none/.test(editor));
check('textarea keeps its own scroll (overflow: auto)', !!editor && /overflow:\s*auto/.test(editor));

// The overlay layers must not grow the box themselves.
const pre = ruleBlock(css, '.yaml-highlight');
check('highlight stays pinned to the box (absolute inset 0)', !!pre && /position:\s*absolute/.test(pre) && /inset:\s*0/.test(pre));
check('highlight does not scroll on its own (overflow: hidden)', !!pre && /overflow:\s*hidden/.test(pre));
check('highlight has no height of its own (would desync from the editor)', !!pre && !/(^|[;\s])height\s*:/.test(pre));

const gutter = ruleBlock(css, '.yaml-gutter');
check('gutter does not stretch the wrap (overflow: hidden)', !!gutter && /overflow:\s*hidden/.test(gutter));
check('gutter has no height of its own (would stretch the wrap)', !!gutter && !/(^|[;\s])height\s*:/.test(gutter));

const area = ruleBlock(css, '.yaml-code-area');
check('code area clips its content (overflow: hidden)', !!area && /overflow:\s*hidden/.test(area));

if (failures) {
  console.log(`\n${failures} failure(s)`);
  process.exit(1);
}
console.log('\nAll regles-styles contract tests passed.');
