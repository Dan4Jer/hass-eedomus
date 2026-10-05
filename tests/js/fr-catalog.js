'use strict';

/**
 * Panel catalog fixtures for the node-run panel tests (CAP-3).
 *
 * tests/fixtures/panel-catalog.json is the committed snapshot of
 * custom_components/eedomus/panel_translations.py — both locale
 * trees, exactly what the eedomus/get_translations command serves.
 * The JS side never parses the Python source anymore: the fixture is
 * the repo-owned input of the JS harness and the i18n guard, and the
 * pytest drift-check pins fixture ≡ PANEL_TRANSLATIONS so the two can
 * never drift apart.
 */

const fs = require('fs');
const path = require('path');

const CATALOG_PATH = path.resolve(
  __dirname,
  '..',
  'fixtures',
  'panel-catalog.json'
);

// {en: {...}, fr: {...}} — the whole frozen catalog.
function loadCatalogs() {
  return JSON.parse(fs.readFileSync(CATALOG_PATH, 'utf8'));
}

function loadFrCatalog() {
  return loadCatalogs().fr;
}

function loadEnCatalog() {
  return loadCatalogs().en;
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
  loadCatalogs,
  loadFrCatalog,
  loadEnCatalog,
  catalogTranslator,
};
