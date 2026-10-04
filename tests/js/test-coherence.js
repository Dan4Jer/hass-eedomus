'use strict';

/**
 * Node-run tests for the coherence pure helpers (ticket 2.3).
 *
 * The panel is a plain browser script with no build toolchain, so this
 * loads it in a vm with stubbed browser globals and asserts on the
 * top-level pure functions exported by the module scope.
 *
 * Run: node tests/js/test-coherence.js (exit 0 on success)
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const PANEL_PATH = path.resolve(
  __dirname,
  '..',
  '..',
  'custom_components',
  'eedomus',
  'www',
  'eedomus-panel.js'
);

const sandbox = {
  HTMLElement: class {},
  customElements: { get: () => true, define() {} },
  window: {
    addEventListener() {},
    removeEventListener() {},
    location: { hash: '' },
  },
};
sandbox.window.window = sandbox.window;
vm.createContext(sandbox);

// Function declarations at the script top level are reachable from an
// appended hook in the same script scope.
const hook = `
;globalThis.__coherence = {
  coherenceToVerify,
  coherenceCompare,
  coherenceSortValue,
  coherenceType,
  filterCoherenceRows,
  nextCoherenceSort,
};`;
vm.runInContext(fs.readFileSync(PANEL_PATH, 'utf8') + hook, sandbox);
const {
  coherenceToVerify,
  coherenceCompare,
  coherenceSortValue,
  coherenceType,
  filterCoherenceRows,
  nextCoherenceSort,
} = sandbox.__coherence;

let failures = 0;
function assertEq(label, actual, expected) {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (a === e) {
    console.log(`PASS  ${label}`);
  } else {
    failures += 1;
    console.log(`FAIL  ${label}`);
    console.log(`      expected ${e}`);
    console.log(`      actual   ${a}`);
  }
}

// Payload in response order (deliberately not sorted).
const ROWS = [
  { periph_id: '101', name: 'Salon', entity_id: 'sensor.salon',
    ha_entity: 'sensor', ha_subtype: 'temperature', signals: [] },
  { periph_id: '12', name: 'Cave', entity_id: null,
    ha_entity: 'sensor', ha_subtype: null, signals: ['sans_entite'] },
  { periph_id: '7', name: 'Garage', entity_id: 'light.garage',
    ha_entity: 'light', ha_subtype: 'switch',
    signals: ['douteux', 'regle_active'] },
  { periph_id: '99', name: 'Bureau', entity_id: 'binary_sensor.bureau',
    ha_entity: 'binary_sensor', ha_subtype: 'opening',
    signals: ['regle_active'] },
  { periph_id: '200', name: 'Cellier', entity_id: 'cover.cellier',
    ha_entity: 'cover', ha_subtype: null, signals: ['en_erreur'] },
];
const ids = (rows) => rows.map((r) => r.periph_id);
const state = (over) =>
  Object.assign({ search: '', view: 'all', sort: { key: null, dir: null } }, over);

// --- sort cycle: croissant -> décroissant -> neutre (ordre de réponse) ---
assertEq(
  'cycle: 1st click croissant',
  nextCoherenceSort({ key: null, dir: null }, 'name'),
  { key: 'name', dir: 'asc' }
);
assertEq(
  'cycle: 2nd click décroissant',
  nextCoherenceSort({ key: 'name', dir: 'asc' }, 'name'),
  { key: 'name', dir: 'desc' }
);
assertEq(
  'cycle: 3rd click neutre',
  nextCoherenceSort({ key: 'name', dir: 'desc' }, 'name'),
  { key: null, dir: null }
);
assertEq(
  'cycle: other column restarts croissant',
  nextCoherenceSort({ key: 'name', dir: 'desc' }, 'periph_id'),
  { key: 'periph_id', dir: 'asc' }
);
assertEq(
  'neutral restores response order',
  ids(filterCoherenceRows(ROWS, state())),
  ids(ROWS)
);
assertEq(
  'periph_id asc is numeric (7 < 12 < 101)',
  ids(filterCoherenceRows(ROWS, state({ sort: { key: 'periph_id', dir: 'asc' } }))),
  ['7', '12', '99', '101', '200']
);
assertEq(
  'periph_id desc is numeric',
  ids(filterCoherenceRows(ROWS, state({ sort: { key: 'periph_id', dir: 'desc' } }))),
  ['200', '101', '99', '12', '7']
);
assertEq(
  'name asc uses locale order',
  filterCoherenceRows(ROWS, state({ sort: { key: 'name', dir: 'asc' } }))
    .map((r) => r.name),
  ['Bureau', 'Cave', 'Cellier', 'Garage', 'Salon']
);

// --- filter-then-sort composition ---
assertEq(
  'view + search + sort compose (filter first, then sort)',
  ids(filterCoherenceRows(ROWS, state({
    view: 'to_verify',
    search: 'e',
    sort: { key: 'periph_id', dir: 'asc' },
  }))),
  ['7', '12', '99', '200']
);
assertEq(
  'sort never mutates the payload',
  ids(ROWS),
  ['101', '12', '7', '99', '200']
);

// --- case-insensitive search on name and periph_id ---
assertEq(
  'search by name is case-insensitive',
  ids(filterCoherenceRows(ROWS, state({ search: 'GARAGE' }))),
  ['7']
);
assertEq(
  'search by periph_id',
  ids(filterCoherenceRows(ROWS, state({ search: '10' }))),
  ['101']
);
assertEq(
  'search with no match',
  filterCoherenceRows(ROWS, state({ search: 'zzz' })),
  []
);

// --- to_verify predicate ---
assertEq(
  'to_verify keeps only signaled rows',
  ids(filterCoherenceRows(ROWS, state({ view: 'to_verify' }))),
  ['12', '7', '99', '200']
);
assertEq(
  'predicate: no signal is false',
  coherenceToVerify({ signals: [] }),
  false
);
assertEq(
  'predicate: unknown signal string is true',
  coherenceToVerify({ signals: ['signal_inconnu'] }),
  true
);

// --- Statut severity tie-break for equal signal counts ---
assertEq(
  'status asc: count first, severity breaks ties',
  ids(filterCoherenceRows(ROWS, state({ sort: { key: 'status', dir: 'asc' } }))),
  ['101', '200', '12', '99', '7']
);
assertEq(
  'status desc: most signals first, severity reversed',
  ids(filterCoherenceRows(ROWS, state({ sort: { key: 'status', dir: 'desc' } }))),
  ['7', '99', '12', '200', '101']
);
assertEq(
  'severity: en_erreur before sans_entite at equal counts',
  coherenceCompare(
    { signals: ['sans_entite'] },
    { signals: ['en_erreur'] },
    'status'
  ) > 0,
  true
);
assertEq(
  'severity: unknown signal ranks after regle_active',
  coherenceCompare(
    { signals: ['regle_active'] },
    { signals: ['signal_inconnu'] },
    'status'
  ),
  -1
);

// --- sort value robustness (null / non-string never throws) ---
assertEq(
  'null name sorts as empty string',
  coherenceSortValue({ name: null }, 'name'),
  ''
);
assertEq(
  'number periph_id is coerced',
  coherenceSortValue({ periph_id: 42 }, 'periph_id'),
  '42'
);
assertEq(
  'null entity_id sorts as empty string',
  coherenceSortValue({ entity_id: null }, 'entity_id'),
  ''
);

// --- shared type helper ---
assertEq(
  'type: mapped identity',
  coherenceType({ ha_entity: 'sensor', ha_subtype: 'temperature' }),
  'sensor / temperature'
);
assertEq(
  'type: platform/class fallback',
  coherenceType({ platform: 'light', device_class: 'switch' }),
  'light / switch'
);

if (failures) {
  console.log(`\n${failures} failure(s)`);
  process.exit(1);
}
console.log('\nAll coherence tests passed.');
