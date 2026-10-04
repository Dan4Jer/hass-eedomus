'use strict';

/**
 * FR catalog loader for the node-run panel tests (CAP-3).
 *
 * Parses the frozen custom_components/eedomus/panel_translations.py —
 * the same 136 panel.* texts the eedomus/get_translations command
 * serves — so the JS harness and the i18n guard never drift from the
 * Python source of truth. No Python execution: the catalog is scanned
 * as the flat dict literal it is (double-quoted keys and values,
 * parenthesized implicit string concatenation — the only shapes the
 * frozen file uses); any other shape fails the test loudly.
 */

const fs = require('fs');
const path = require('path');

const CATALOG_PATH = path.resolve(
  __dirname,
  '..',
  '..',
  'custom_components',
  'eedomus',
  'panel_translations.py'
);

// One double-quoted Python string: standard escapes only.
function readQuoted(src, i) {
  let out = '';
  i += 1; // past the opening quote
  while (i < src.length) {
    const c = src[i];
    if (c === '\\') {
      const n = src[i + 1];
      out += n === 'n' ? '\n' : n === 't' ? '\t' : n;
      i += 2;
      continue;
    }
    if (c === '"') {
      return [out, i + 1];
    }
    out += c;
    i += 1;
  }
  throw new Error('unterminated string in panel_translations.py');
}

// Whitespace and # comments between dict entries.
function skipSpaceAndComments(src, i) {
  while (i < src.length) {
    const c = src[i];
    if (c === '#' ) {
      while (i < src.length && src[i] !== '\n') {
        i += 1;
      }
    } else if (c === ' ' || c === '\n' || c === '\r' || c === '\t') {
      i += 1;
    } else {
      break;
    }
  }
  return i;
}

// Flat {key: value} dict starting at src[start] === '{'. Values are a
// double-quoted string or a parenthesized concatenation of them.
function parseLocaleDict(src, start) {
  const dict = {};
  let i = skipSpaceAndComments(src, start + 1);
  while (i < src.length && src[i] !== '}') {
    if (src[i] !== '"') {
      throw new Error(`unexpected catalog char: ${JSON.stringify(src[i])}`);
    }
    let key;
    let value;
    [key, i] = readQuoted(src, i);
    i = skipSpaceAndComments(src, i);
    if (src[i] !== ':') {
      throw new Error(`expected ':' after catalog key ${key}`);
    }
    i = skipSpaceAndComments(src, i + 1);
    if (src[i] === '(') {
      i = skipSpaceAndComments(src, i + 1);
      value = '';
      while (src[i] !== ')') {
        if (src[i] !== '"') {
          throw new Error(`expected string in concatenation for ${key}`);
        }
        let part;
        [part, i] = readQuoted(src, i);
        value += part;
        i = skipSpaceAndComments(src, i);
      }
      i += 1; // past ')'
    } else {
      [value, i] = readQuoted(src, i);
    }
    dict[key] = value;
    i = skipSpaceAndComments(src, i);
    if (src[i] === ',') {
      i = skipSpaceAndComments(src, i + 1);
    }
  }
  return dict;
}

function parseFrCatalog(source) {
  const marker = '"fr": {';
  const start = source.indexOf(marker);
  if (start === -1) {
    throw new Error('"fr" catalog not found in panel_translations.py');
  }
  return parseLocaleDict(source, start + marker.length - 1);
}

function loadFrCatalog() {
  return parseFrCatalog(fs.readFileSync(CATALOG_PATH, 'utf8'));
}

// Translator mirroring the panel's t() over a plain catalog object —
// what the pure helpers receive from the tests.
function catalogTranslator(catalog) {
  return (key, params) => {
    const text = catalog[key] || key;
    if (!params) {
      return text;
    }
    return text.replace(/\{(\w+)\}/g, (match, name) =>
      params[name] === undefined || params[name] === null
        ? match
        : String(params[name])
    );
  };
}

module.exports = {
  CATALOG_PATH,
  parseFrCatalog,
  loadFrCatalog,
  catalogTranslator,
};
