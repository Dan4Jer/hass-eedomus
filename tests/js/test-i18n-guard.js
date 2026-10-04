'use strict';

/**
 * i18n guard (CAP-3, ticket 3.3): NO user-facing FR text may remain
 * hardcoded in the panel script — every string ships through the
 * eedomus/get_translations catalog.
 *
 * How it works:
 * 1. A small state-machine scanner extracts every string and template
 *    literal of custom_components/eedomus/www/eedomus-panel.js,
 *    skipping comments (the French code comments belong to 3.5) and
 *    regex bodies; ${...} interpolations of templates collapse to a
 *    {x} placeholder.
 * 2. Each literal is prepared the same way — inline <svg>...</svg>
 *    markup and comment-shaped text (CSS /* *\/, HTML <!-- -->) inside
 *    templates are stripped (icons and comments are not user-facing
 *    strings) — then normalized (placeholders -> {x}, whitespace
 *    collapsed and trimmed) and checked against the FR reference set:
 *    equality, plus the same letter-bearing substring rule for quoted
 *    literals and templates alike (a template embeds its text inside
 *    markup, a quoted literal may carry the text with extra words).
 * 3. The FR reference set is the frozen catalog's FR column
 *    (panel_translations.py — the exact texts the
 *    eedomus/get_translations command serves, via
 *    tests/js/fr-catalog.js; several keys may normalize to the same
 *    text, so violations report every matching key). The i18n
 *    inventory's Current column is prose shorthand (" / " composites,
 *    "…", "title {msg}", "aria") that cannot be matched literally, so
 *    instead the guard parses the inventory THE SAME WAY the Python
 *    parity test does — the Key column with its '/' expansion — and
 *    asserts the catalog's key set equals it: the catalog texts are
 *    thereby pinned to the inventory before any FR text is checked.
 * 4. Every panel.* literal used by the migration is validated against
 *    the catalog's key set — a typo'd key fails the guard.
 * 5. A French-marker heuristic (accented Latin letters, guillemets)
 *    fails any NEW hardcoded French even when it matches no catalog
 *    text.
 *
 * Explicit exemptions (a skipped literal never matches):
 * - literals with no letter and no digit (pure punctuation/symbols,
 *   e.g. the '?' fallback — no language to hardcode);
 * - eedomus/... websocket types and the hass-more-info event name;
 * - TECHNICAL_TOKENS: identifiers that double as data keys and as
 *   same-in-every-language catalog labels ('periph_id' is the sort key
 *   AND the FR column label — the label must come from t(), the key
 *   stays a literal). CSS classes, DOM ids, hash values and attribute
 *   names never equal an FR text, so they need no exemption entry.
 *
 * The test FAILS the moment any FR text is reintroduced as a literal
 * and passes only when the migration is complete.
 *
 * Run: node tests/js/test-i18n-guard.js (exit 0 on success)
 */

const fs = require('fs');
const path = require('path');
const { loadFrCatalog } = require('./fr-catalog');

const PANEL_PATH = path.resolve(
  __dirname,
  '..',
  '..',
  'custom_components',
  'eedomus',
  'www',
  'eedomus-panel.js'
);
const INVENTORY_PATH = path.resolve(
  __dirname,
  '..',
  '..',
  '_bmad-output',
  'specs',
  'spec-eedomus-i18n',
  'i18n-inventory.md'
);

// ---- literal extraction ----------------------------------------------

// Standard JS escapes of quoted strings, decoded for comparison.
function unescapeJs(raw) {
  return raw.replace(/\\(.)/g, (match, c) => {
    if (c === 'n') {
      return '\n';
    }
    if (c === 't') {
      return '\t';
    }
    return c;
  });
}

// A regex literal may follow these characters (value positions);
// otherwise '/' is a division operator (none in the panel script).
const REGEX_ALLOWED_AFTER = new Set([
  '', '(', ',', '=', ':', '[', '!', '&', '|', '?', '{', ';',
  '+', '-', '*', '%', '<', '>', '~', '^',
]);

function extractLiterals(src) {
  const literals = [];
  const tplStack = []; // template buffers, outermost first
  const exprStack = []; // open brace counts of ${...} frames
  let mode = 'code'; // code | str | tpl | linec | blockc | regex
  let strQuote = '';
  let strBuf = '';
  let regexClass = false;
  let lastSig = ''; // last significant char seen in code context
  let line = 1;

  const emit = (text, quote) => {
    literals.push({ text, quote, line });
  };

  for (let i = 0; i < src.length; i++) {
    const c = src[i];
    const n = src[i + 1];
    if (c === '\n') {
      line += 1;
    }
    switch (mode) {
      case 'linec':
        if (c === '\n') {
          mode = 'code';
        }
        break;
      case 'blockc':
        if (c === '*' && n === '/') {
          mode = 'code';
          i += 1;
        }
        break;
      case 'str':
        if (c === '\\') {
          strBuf += c + (n === '\n' ? '' : n);
          if (n === '\n') {
            line += 1;
          }
          i += 1;
        } else if (c === strQuote) {
          emit(unescapeJs(strBuf), strQuote);
          mode = 'code';
          lastSig = 'x';
        } else {
          strBuf += c;
        }
        break;
      case 'regex':
        if (c === '\\') {
          i += 1;
        } else if (c === '[') {
          regexClass = true;
        } else if (c === ']') {
          regexClass = false;
        } else if (c === '/' && !regexClass) {
          mode = 'code';
          lastSig = 'x';
        }
        break;
      case 'tpl':
        if (c === '\\') {
          tplStack[tplStack.length - 1] += c + (n || '');
          i += 1;
        } else if (c === '`') {
          emit(tplStack.pop(), 'tpl');
          mode = 'code';
          lastSig = 'x';
        } else if (c === '$' && n === '{') {
          exprStack.push(0);
          mode = 'code';
          i += 1;
        } else {
          tplStack[tplStack.length - 1] += c;
        }
        break;
      default:
        if (/\s/.test(c)) {
          break;
        }
        if (c === '/' && n === '/') {
          mode = 'linec';
          i += 1;
        } else if (c === '/' && n === '*') {
          mode = 'blockc';
          i += 1;
        } else if (c === "'" || c === '"') {
          mode = 'str';
          strQuote = c;
          strBuf = '';
          lastSig = c;
        } else if (c === '`') {
          tplStack.push('');
          mode = 'tpl';
          lastSig = c;
        } else if (c === '/' && REGEX_ALLOWED_AFTER.has(lastSig)) {
          mode = 'regex';
          regexClass = false;
          lastSig = 'x';
        } else if (c === '{') {
          if (exprStack.length) {
            exprStack[exprStack.length - 1] += 1;
          }
          lastSig = c;
        } else if (c === '}' && exprStack.length) {
          const depth = exprStack[exprStack.length - 1];
          if (depth === 0) {
            // The ${...} frame closes: back to the enclosing template.
            exprStack.pop();
            tplStack[tplStack.length - 1] += '{x}';
            mode = 'tpl';
          } else {
            exprStack[exprStack.length - 1] = depth - 1;
          }
          lastSig = c;
        } else {
          lastSig = c;
        }
        break;
    }
  }
  return literals;
}

// ---- literal preparation ---------------------------------------------

// Inline SVG icons: markup and path data, not user-facing strings.
function stripSvgMarkup(text) {
  return text.replace(/<svg[\s\S]*?<\/svg>/g, ' ');
}

// Comment-shaped text inside template literals (CSS and HTML comment
// syntax): the French comments belong to the 3.5 pass, not the strings.
function stripInlineComments(text) {
  return text
    .replace(/\/\*[\s\S]*?\*\//g, ' ')
    .replace(/<!--[\s\S]*?-->/g, ' ');
}

function normalize(text) {
  return String(text)
    .replace(/\$\{[^}]*\}/g, '{x}')
    .replace(/\{[^{}]*\}/g, '{x}')
    .replace(/\s+/g, ' ')
    .trim();
}

// ---- inventory parity (mirrors the Python unit test) -----------------

// The inventory's Key column with its '/' shorthand: a suffix replaces
// the last segment of the base key (a bare token replaces it entirely).
function inventoryPanelKeys() {
  const text = fs.readFileSync(INVENTORY_PATH, 'utf8');
  const section = text.split('## 1.')[1].split('## 2.')[0];
  const keys = new Set();
  for (const line of section.split('\n')) {
    if (!line.startsWith('|')) {
      continue;
    }
    const cells = line
      .trim()
      .replace(/^\|/, '')
      .replace(/\|$/, '')
      .split('|')
      .map((cell) => cell.trim());
    const keyCell = cells[cells.length - 1];
    if (!keyCell.startsWith('panel.')) {
      continue;
    }
    const tokens = keyCell.split('/').map((token) => token.trim());
    const base = tokens[0];
    keys.add(base);
    for (const suffix of tokens.slice(1)) {
      if (suffix.startsWith('.')) {
        keys.add(base.slice(0, base.lastIndexOf('.')) + suffix);
      } else {
        keys.add(suffix);
      }
    }
  }
  return keys;
}

// ---- exemptions ------------------------------------------------------

// Data keys that double as same-in-every-language catalog labels: the
// LABEL must come from t(), the KEY stays a literal.
const TECHNICAL_TOKENS = new Set([
  'periph_id',
  'ha_entity',
  'ha_subtype',
  'usage_id',
]);

function isExempt(raw, text) {
  if (!/[A-Za-z0-9]/.test(text)) {
    return true; // pure punctuation/symbols — no language to hardcode
  }
  if (/^eedomus\//.test(raw)) {
    return true; // websocket command types
  }
  if (raw === 'hass-more-info') {
    return true; // HA event type
  }
  if (TECHNICAL_TOKENS.has(raw)) {
    return true;
  }
  return false;
}

// French-marker heuristic: accented Latin letters or guillemets.
const FRENCH_MARKER = /[\u00C0-\u017F\u00AB\u00BB]/;

// ---- the guard --------------------------------------------------------

const src = fs.readFileSync(PANEL_PATH, 'utf8');
const literals = extractLiterals(src);

// Reference set: the frozen catalog FR texts — pinned to the inventory
// first (same key-column parsing as the Python parity test).
const catalogFr = loadFrCatalog();
const catalogKeys = new Set(Object.keys(catalogFr));
const inventoryKeys = inventoryPanelKeys();
const missingInCatalog = [...inventoryKeys].filter((k) => !catalogKeys.has(k));
const extraInCatalog = [...catalogKeys].filter((k) => !inventoryKeys.has(k));
if (missingInCatalog.length || extraInCatalog.length) {
  console.log('FAIL  the catalog and the i18n inventory key column diverged');
  if (missingInCatalog.length) {
    console.log(
      `      inventory keys missing from the catalog: ${missingInCatalog.join(', ')}`
    );
  }
  if (extraInCatalog.length) {
    console.log(
      `      catalog keys absent from the inventory: ${extraInCatalog.join(', ')}`
    );
  }
  process.exit(1);
}

// Normalized FR text -> every catalog key carrying it (several keys may
// normalize to the same text — provenance reports them all).
const frTexts = new Map();
for (const [key, value] of Object.entries(catalogFr)) {
  const norm = normalize(value);
  if (!norm) {
    continue;
  }
  if (!frTexts.has(norm)) {
    frTexts.set(norm, []);
  }
  frTexts.get(norm).push(key);
}

const violations = [];
let checked = 0;
let exempted = 0;
let migratedKeys = 0;

for (const literal of literals) {
  const raw = literal.text;
  if (/^panel\.[a-z0-9_.]+$/.test(raw)) {
    // The migration itself: a t() key argument — but it must exist in
    // the catalog, a typo'd key renders as literal key text.
    migratedKeys += 1;
    if (!catalogKeys.has(raw)) {
      violations.push({
        line: literal.line,
        literal: raw,
        fr: raw,
        provenance: 'unknown panel.* key (not in the catalog)',
      });
    }
    continue;
  }
  const text = stripInlineComments(stripSvgMarkup(raw));
  if (isExempt(raw, text)) {
    exempted += 1;
    continue;
  }
  checked += 1;
  const norm = normalize(text);
  if (!norm) {
    continue;
  }
  let matched = false;
  // One substring rule for quoted literals and templates alike: any FR
  // text appearing inside the literal — embedded in markup, or with
  // extra words around it — is a hardcoded string, and an exact match
  // is the substring of itself. Texts without a letter of their own
  // ("{raw}", "{error_message}") normalize to "{x}" and match every
  // interpolation, so only texts carrying a letter (length >= 3)
  // participate.
  for (const [fr, keys] of frTexts) {
    const core = fr.replace(/\{x\}/g, '');
    if (fr.length >= 3 && /[A-Za-z]/.test(core) && norm.includes(fr)) {
      violations.push({
        line: literal.line,
        literal: norm.slice(0, 100),
        fr,
        provenance: `catalog ${keys.join(', ')}`,
      });
      matched = true;
    }
  }
  // French marker: any NEW hardcoded French fails even when it matches
  // no catalog text (accented Latin letters, guillemets).
  if (!matched && FRENCH_MARKER.test(norm)) {
    violations.push({
      line: literal.line,
      literal: norm.slice(0, 100),
      fr: 'French marker (accented letters or guillemets)',
      provenance: 'hardcoded French outside the catalog',
    });
  }
}

console.log(`i18n guard: ${literals.length} literals scanned, ` +
  `${migratedKeys} migration keys, ${exempted} exempted, ${checked} ` +
  `checked against ${frTexts.size} FR texts (${catalogKeys.size} keys)`);

if (violations.length) {
  const seen = new Set();
  for (const v of violations) {
    const key = `${v.line}:${v.fr}:${v.provenance}`;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    console.log(`FAIL  line ${v.line}: hardcoded FR text`);
    console.log(`      literal: ${v.literal}`);
    console.log(`      matches: ${v.fr} (${v.provenance})`);
  }
  console.log(`\n${seen.size} hardcoded FR text(s) — migrate to a ` +
    'panel.* key through t().');
  process.exit(1);
}
console.log('No hardcoded FR text — all user-facing strings come ' +
  'from the catalog.');
