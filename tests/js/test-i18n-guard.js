'use strict';

/**
 * i18n guard (CAP-3, ticket 3.3): NO user-facing text may remain
 * hardcoded in the panel script — every string ships through the
 * eedomus/get_translations catalog.
 *
 * How it works:
 * 1. A small state-machine scanner extracts every string and template
 *    literal of EVERY JS file of custom_components/eedomus/www/ — the
 *    entry eedomus-panel.js and the www/panel/*.js ES modules (the
 *    panel's surface is the whole file set) — skipping comments (the
 *    French code comments belong to 3.5) and regex bodies; ${...}
 *    interpolations of templates collapse to a {x} placeholder.
 * 2. Each literal is prepared the same way — inline <svg>...</svg>
 *    markup and comment-shaped text (CSS /* *\/, HTML <!-- -->) inside
 *    templates are stripped (icons and comments are not user-facing
 *    strings) — then normalized (placeholders -> {x}, whitespace
 *    collapsed and trimmed).
 * 3. The reference set is the UNION of the EN and FR catalog trees
 *    (tests/fixtures/panel-catalog.json — the committed snapshot of
 *    panel_translations.py, drift-checked against it by pytest): a
 *    hardcoded EN string fails exactly like a hardcoded FR one.
 *    Exact equality fails at any length; the substring rule needs a
 *    reference core of at least 8 letters/digits so short texts never
 *    fire on incidental fragments (a template embeds its text inside
 *    markup, a quoted literal may carry the text with extra words).
 * 4. The French-marker heuristic (accented Latin letters, guillemets)
 *    runs BEFORE the no-alnum exemption exit: a bare «» pair is as
 *    hardcoded as a sentence. FR stopwords (le/la/les/dans/…) fail
 *    on exact match — French without accents and without catalog
 *    text is still French.
 * 5. Every panel.* literal used by the migration is validated against
 *    the catalog's key set (pinned to the fixture key list first) — a
 *    typo'd key fails the guard.
 *
 * Explicit exemptions (a skipped literal never matches the reference):
 * - eedomus/... websocket types and the hass-more-info event name;
 * - TECHNICAL_TOKENS: identifiers that double as data keys and as
 *   same-in-every-language catalog labels ('periph_id' is the sort key
 *   AND the column label — the label must come from t(), the key
 *   stays a literal). CSS classes, DOM ids, hash values and attribute
 *   names never equal a catalog text, so they need no exemption entry.
 *
 * The test FAILS the moment any catalog text is reintroduced as a
 * literal (either language) and passes only when the migration is
 * complete.
 *
 * Run: node tests/js/test-i18n-guard.js (exit 0 on success)
 */

const fs = require('fs');
const path = require('path');
const { loadCatalogs } = require('./fr-catalog');

const PANEL_PATH = path.resolve(
  __dirname,
  '..',
  '..',
  'custom_components',
  'eedomus',
  'www',
  'eedomus-panel.js'
);
// The panel's surface is the whole www/ tree: every .js file under it
// (the entry, today's panel/ modules, any future subfolder) collected
// by a recursive walk — a hardcoded list would let a new module
// silently escape the scan. A missing/unreadable dir fails with the
// path, not a raw ENOENT.
const PANEL_DIR = path.dirname(PANEL_PATH);
function collectPanelFiles(dir) {
  let names;
  try {
    names = fs.readdirSync(dir);
  } catch (err) {
    throw new Error(`panel www dir missing or unreadable: ${dir}`);
  }
  const files = [];
  for (const name of names.sort()) {
    const full = path.join(dir, name);
    let stats;
    try {
      stats = fs.statSync(full);
    } catch (err) {
      throw new Error(`panel www entry unreadable: ${full}`);
    }
    if (stats.isDirectory()) {
      files.push(...collectPanelFiles(full));
    } else if (name.endsWith('.js')) {
      files.push(full);
    }
  }
  return files;
}
const PANEL_FILES = collectPanelFiles(PANEL_DIR);
const KEYS_PATH = path.resolve(
  __dirname,
  '..',
  'fixtures',
  'panel-keys.json'
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
// otherwise '/' is a division operator.
const REGEX_ALLOWED_AFTER = new Set([
  '', '(', ',', '=', ':', '[', '!', '&', '|', '?', '{', ';',
  '+', '-', '*', '%', '<', '>', '~', '^',
]);
// After a closing paren or bracket a '/' is always division, never a
// regex start: entering regex mode here would swallow the rest of the
// line as a pattern body (e.g. `Math.max(a, b) / 2`).
const DIVISION_AFTER = new Set([')', ']']);

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
        } else if (c === '/' && DIVISION_AFTER.has(lastSig)) {
          lastSig = '/';
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

// ---- fixture parity (mirrors the Python drift-check) -----------------

// The committed key list generated once from the i18n inventory's Key
// column: the guard pins the catalog's key set against it before any
// text is checked.
function fixturePanelKeys() {
  return new Set(JSON.parse(fs.readFileSync(KEYS_PATH, 'utf8')));
}

// ---- exemptions ------------------------------------------------------

// Data keys that double as catalog labels in one language or another:
// the LABEL must come from t(), the KEY stays a literal ('modified'
// is the diff-op type and the row flag, 'unknown' the chip class
// suffix — their EN column labels are "modified" and "unknown").
const TECHNICAL_TOKENS = new Set([
  'periph_id',
  'ha_entity',
  'ha_subtype',
  'usage_id',
  'modified',
  'unknown',
]);

function isExempt(raw, text) {
  if (/^eedomus\//.test(raw)) {
    return true; // websocket command types
  }
  if (raw === 'hass-more-info') {
    return true; // HA event type
  }
  if (TECHNICAL_TOKENS.has(raw)) {
    return true;
  }
  if (!/[A-Za-z0-9]/.test(text)) {
    return true; // pure punctuation/symbols — no language to hardcode
  }
  return false;
}

// French-marker heuristic: accented Latin letters or guillemets.
const FRENCH_MARKER = /[\u00C0-\u017F\u00AB\u00BB]/;

// French stopwords (accent-free, single words): hardcoded French that
// matches no catalog text and carries no marker still fails on exact
// equality — "le" as a literal is never an English identifier here.
const STOPWORDS_FR = new Set([
  'le', 'la', 'les', 'un', 'une', 'des', 'du', 'dans', 'pour',
  'avec', 'sans', 'sur', 'par', 'pas', 'plus', 'est', 'et', 'ou',
  'au', 'aux', 'ce', 'cet', 'cette', 'que', 'qui', 'ne', 'non',
  'oui', 'si',
]);

// ---- the guard --------------------------------------------------------

// Reference set: the UNION of the EN and FR catalog trees (fixture),
// pinned to the committed key list first. Both trees are checked: a
// key missing from either side silently degrades the panel.
const catalogs = loadCatalogs();
const catalogKeysEn = new Set(Object.keys(catalogs.en));
const catalogKeysFr = new Set(Object.keys(catalogs.fr));
const catalogKeys = new Set([...catalogKeysEn, ...catalogKeysFr]);
const fixtureKeys = fixturePanelKeys();
const missingInCatalog = [...fixtureKeys].filter(
  (k) => !catalogKeysEn.has(k) || !catalogKeysFr.has(k)
);
const extraInCatalog = [...catalogKeys].filter((k) => !fixtureKeys.has(k));
if (missingInCatalog.length || extraInCatalog.length) {
  console.log('FAIL  the catalog and the panel key fixture diverged');
  if (missingInCatalog.length) {
    console.log(
      `      fixture keys missing from a catalog tree: ${missingInCatalog.join(', ')}`
    );
  }
  if (extraInCatalog.length) {
    console.log(
      `      catalog keys absent from the fixture: ${extraInCatalog.join(', ')}`
    );
  }
  process.exit(1);
}

// Normalized text -> every (locale, key) side carrying it (several keys
// may normalize to the same text — provenance reports them all). Pure
// placeholder texts ("{raw}", "{msg}") carry no language of their own:
// every template interpolation normalizes to "{x}" and would match
// them all — they never join the reference.
const reference = new Map();
for (const [locale, tree] of Object.entries(catalogs)) {
  for (const [key, value] of Object.entries(tree)) {
    const norm = normalize(value);
    const core = norm.replace(/\{x\}/g, '').replace(/\s/g, '');
    if (!norm || !/[A-Za-z0-9]/.test(core)) {
      continue;
    }
    if (!reference.has(norm)) {
      reference.set(norm, []);
    }
    reference.get(norm).push({ locale, key });
  }
}

// The literal-checking pipeline, factored so the committed self-test
// below runs the exact same code path as the real scan.
function checkLiterals(literals) {
  const violations = [];
  let checked = 0;
  let exempted = 0;
  let migratedKeys = 0;

  for (const literal of literals) {
    const raw = literal.text;
    if (/^panel\.[A-Za-z0-9_.]+$/.test(raw)) {
      // The migration itself: a t() key argument — but it must exist in
      // the catalog, a typo'd key renders as literal key text.
      migratedKeys += 1;
      if (!catalogKeys.has(raw)) {
        violations.push({
          line: literal.line,
          literal: raw,
          matched: raw,
          provenance: 'unknown panel.* key (not in the catalog)',
        });
      }
      continue;
    }
    const text = stripInlineComments(stripSvgMarkup(raw));
    const norm = normalize(text);
    if (!norm) {
      continue;
    }
    // French marker first, BEFORE any exemption exit: a bare guillemet
    // pair or an accented fragment is hardcoded French even when the
    // literal carries no letter or digit of its own.
    if (FRENCH_MARKER.test(norm)) {
      violations.push({
        line: literal.line,
        literal: norm.slice(0, 100),
        matched: 'French marker (accented letters or guillemets)',
        provenance: 'hardcoded French outside the catalog',
      });
      continue;
    }
    // Accent-free French: a bare stopword is never a technical token in
    // this panel.
    if (STOPWORDS_FR.has(norm)) {
      violations.push({
        line: literal.line,
        literal: norm.slice(0, 100),
        matched: `French stopword "${norm}"`,
        provenance: 'hardcoded French outside the catalog',
      });
      continue;
    }
    if (isExempt(raw, text)) {
      exempted += 1;
      continue;
    }
    checked += 1;
    // Exact equality fails at any length and in either language: the
    // reference carries both sides, a hardcoded EN string is as much a
    // regression as a hardcoded FR one.
    const exact = reference.get(norm);
    if (exact) {
      violations.push({
        line: literal.line,
        literal: norm.slice(0, 100),
        matched: norm,
        provenance: `catalog ${exact
          .map((side) => `${side.key} (${side.locale})`)
          .join(', ')}`,
      });
      continue;
    }
    // Substring rule: a reference text embedded in the literal (markup
    // around it, extra words beside it). Only texts with a core of at
    // least 8 letters/digits participate — shorter texts (labels like
    // "Retry") never fire on incidental fragments. Technical tokens
    // never participate: their legitimate home is inside literals as
    // data keys and class-name fragments, not as user-facing words.
    for (const [refNorm, sides] of reference) {
      const core = refNorm.replace(/\{x\}/g, '');
      if (
        core.length >= 8 &&
        !TECHNICAL_TOKENS.has(refNorm) &&
        norm.includes(refNorm)
      ) {
        violations.push({
          line: literal.line,
          literal: norm.slice(0, 100),
          matched: refNorm,
          provenance: `catalog ${sides
            .map((side) => `${side.key} (${side.locale})`)
            .join(', ')}`,
        });
      }
    }
  }
  return { violations, checked, exempted, migratedKeys };
}

// ---- committed positive control (self-test) -------------------------
// Each hardened rule is exercised against a planted violation through
// the SAME pipeline as the real scan: a rule that stops catching its
// probe fails the guard run itself.
const SELFTEST_PROBES = [
  {
    rule: 'hardcoded EN exact',
    source: 'const probe = "Retry";',
    expect: (v) => v.matched === 'Retry' && v.provenance.includes('(en)'),
  },
  {
    rule: 'EN substring inside a template',
    source: 'const probe = `<p>Configuration applied.</p>`;',
    expect: (v) => v.matched === 'Configuration applied.',
  },
  {
    rule: 'French stopword',
    source: "const probe = 'dans';",
    expect: (v) => v.matched === 'French stopword "dans"',
  },
  {
    rule: 'bare guillemets before the no-alnum exit',
    source: 'const probe = "«»";',
    expect: (v) => v.matched === 'French marker (accented letters or guillemets)',
  },
  {
    // Canary probe: the key below exists in NO catalog on purpose —
    // it is the self-test's synthetic probe, not a real panel key. If
    // this rule ever fails, the guard's own pipeline broke; a real
    // unknown-key regression surfaces in the scan above, which reads
    // the panel source, never this probe. Previously keyed on the
    // dead panel.coherence.status.total, a self-test failure could be
    // misread as a coherence-catalog regression.
    rule: 'unknown panel.* key (canary probe)',
    source: "t('panel.canary.selftest.unknown_key');",
    expect: (v) => v.provenance === 'unknown panel.* key (not in the catalog)',
  },
];

const selftestMissed = [];
for (const probe of SELFTEST_PROBES) {
  const result = checkLiterals(extractLiterals(probe.source));
  if (!result.violations.some(probe.expect)) {
    selftestMissed.push(probe.rule);
    console.log(`FAIL  self-test: the guard missed a planted ${probe.rule}`);
    console.log(`      probe source: ${probe.source}`);
  }
}
if (selftestMissed.length) {
  console.log(
    `\n${selftestMissed.length} self-test rule(s) no longer catch their probe`
  );
  process.exit(1);
}
console.log(
  `self-test: ${SELFTEST_PROBES.length}/${SELFTEST_PROBES.length} planted violations caught`
);

// ---- the scan --------------------------------------------------------
// Every file of the panel surface, one extraction each (line numbers
// stay per-file); the literal pipeline is shared, unchanged.
// Import statements are stripped BEFORE extraction: a module
// specifier ('./panel/shared.js') is wiring, not user-facing text —
// the exemption is scoped by never reaching the checks, so a literal
// that merely starts with "./" still gets checked like any other.
const importRe = /import\s[^;]*?from\s*['"][^'"]+['"]\s*;|import\s*['"][^'"]+['"]\s*;/g;
const fileResults = [];
let literalsScanned = 0;
for (const file of PANEL_FILES) {
  // The match collapses to its own newlines: the statement text is
  // gone for the scanner but every following line keeps its number.
  const fileSrc = fs.readFileSync(file, 'utf8').replace(
    importRe,
    (match) => match.replace(/[^\n]/g, '')
  );
  const fileLiterals = extractLiterals(fileSrc);
  literalsScanned += fileLiterals.length;
  const result = checkLiterals(fileLiterals);
  // Tagged at the source: checkLiterals returns fresh violation
  // records, so the file label rides along instead of a lookup.
  for (const v of result.violations) {
    v.file = path.basename(file);
  }
  fileResults.push(result);
}

const violations = [].concat(...fileResults.map((r) => r.violations));
const checked = fileResults.reduce((sum, r) => sum + r.checked, 0);
const exempted = fileResults.reduce((sum, r) => sum + r.exempted, 0);
const migratedKeys = fileResults.reduce((sum, r) => sum + r.migratedKeys, 0);

console.log(`i18n guard: ${literalsScanned} literals scanned across ` +
  `${PANEL_FILES.length} files, ${migratedKeys} migration keys, ` +
  `${exempted} exempted, ${checked} checked against ` +
  `${reference.size} catalog texts (${catalogKeys.size} keys, EN+FR union)`);

if (violations.length) {
  const seen = new Set();
  for (const v of violations) {
    const key = `${v.file}:${v.line}:${v.matched}:${v.provenance}`;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    console.log(`FAIL  ${v.file} line ${v.line}: ` +
      'hardcoded catalog text');
    console.log(`      literal: ${v.literal}`);
    console.log(`      matches: ${v.matched} (${v.provenance})`);
  }
  console.log(`\n${seen.size} hardcoded text(s) — migrate to a ` +
    'panel.* key through t().');
  process.exit(1);
}
console.log('No hardcoded catalog text (EN or FR) — all user-facing ' +
  'strings come from the catalog.');
