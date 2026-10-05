'use strict';

/**
 * Node-run tests for the coherence pure helpers (ticket 2.3).
 *
 * The panel is a plain browser module set with no build toolchain
 * (entry + ./panel/*.js ES modules), so this loads the whole graph
 * in a vm with stubbed browser globals and asserts on the top-level
 * pure functions shared by the module scopes.
 *
 * Since CAP-3 the label-bearing helpers take a translator as their
 * last argument; the tests pass a fixture built from the committed FR
 * catalog snapshot (tests/fixtures/panel-catalog.json, drift-checked
 * against panel_translations.py by pytest), so the expected texts
 * below stay the real FR panel texts.
 *
 * Run: node tests/js/test-coherence.js (exit 0 on success)
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { loadFrCatalog, catalogTranslator } = require('./fr-catalog');

const PANEL_PATH = path.resolve(
  __dirname,
  '..',
  '..',
  'custom_components',
  'eedomus',
  'www',
  'eedomus-panel.js'
);

// CustomEvent stub: the vm has no DOM — the dispatch test only needs
// type, detail, bubbles and composed to be observable.
class StubCustomEvent {
  constructor(type, opts) {
    this.type = type;
    this.detail = opts && opts.detail ? opts.detail : null;
    this.bubbles = Boolean(opts && opts.bubbles);
    this.composed = Boolean(opts && opts.composed);
  }
}

// Timer stubs (sweep): the debounce test captures scheduled timers
// instead of waiting — flushing is manual, so no test ever depends
// on real timing. Handles are 1-based indices into sandboxTimers.
const sandboxTimers = [];
const sandboxCleared = [];

const sandbox = {
  // attachShadow stub: the constructor calls it — the instances under
  // test never touch a real shadowRoot beyond the guarded noops.
  HTMLElement: class {
    attachShadow() {
      this.shadowRoot = {
        addEventListener() {},
        removeEventListener() {},
      };
      return this.shadowRoot;
    }
  },
  customElements: { get: () => true, define() {} },
  CustomEvent: StubCustomEvent,
  setTimeout: (fn, delay) => {
    sandboxTimers.push({ fn, delay });
    return sandboxTimers.length;
  },
  clearTimeout: (handle) => {
    sandboxCleared.push(handle);
  },
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
  coherenceFieldValue,
  coherenceLiveFields,
  coherenceIdentityFields,
  coherenceRawPairs,
  coherenceRawJson,
  coherencePopoverPosition,
  coherenceTriggerHtml,
  coherenceEntityLinkHtml,
  coherenceHasEntity,
  coherenceRowHtml,
  EedomusConfigPanel,
  coherenceDetailHtml,
  coherenceDetailAttempts,
  nextCoherenceExpanded,
  coherenceIsExpanded,
  coherenceExpandedRowId,
  coherenceExpandedRowHtml,
  coherenceRowExpansionHtml,
  POPOVER_FOCUSABLE_SELECTOR,
  coherenceHeadHtml,
  coherenceChipsHtml,
  coherenceChipHtml,
  COHERENCE_SIGNALS,
  COHERENCE_OK_SIGNAL,
  periphStatusText,
  coherenceStatusText,
  COHERENCE_COLUMNS,
  supervisionChartPoints,
  supervisionLinePath,
  supervisionBarRects,
  supervisionLineChartHtml,
  supervisionBarChartHtml,
  supervisionMetricCardHtml,
  supervisionFormatSeconds,
  supervisionFormatCount,
};`;

// Mini module loader (story 102): the panel is real ES modules — the
// entry eedomus-panel.js imports ./panel/*.js. The vm has no module
// system, so the loader walks the import graph from the entry,
// evaluates the dependencies first, strips the import/export syntax
// and concatenates everything into the single script scope the hook
// reads — the same scope the pre-split panel had. A missing module
// fails loud here; a duplicated top-level name fails loud at
// evaluation (const redeclaration). Only two forms are stripped —
// "import ... from '...';" and a leading "^export ": any other ESM
// form (side-effect import, namespace import, re-export, double
// quotes) is REJECTED loudly instead of failing later as an
// unrelated vm SyntaxError.
function loadPanelSource() {
  const loaded = [];
  const seen = new Set();
  function walk(file) {
    if (seen.has(file)) {
      return;
    }
    seen.add(file);
    let src;
    try {
      src = fs.readFileSync(file, 'utf8');
    } catch (err) {
      throw new Error(`panel module missing or unreadable: ${file}`);
    }
    const importRe = /import\s[^;]*?from\s*'[^']+'\s*;/g;
    const dir = path.dirname(file);
    const deps = [];
    let match;
    while ((match = importRe.exec(src)) !== null) {
      deps.push(path.resolve(dir, /'([^']+)'/.exec(match[0])[1]));
    }
    deps.forEach(walk);
    const stripped = src
      .replace(importRe, '')
      .replace(/^export (const|function|class) /gm, '$1 ');
    const leftover = stripped.match(/^[ \t]*(import|export)\b/m);
    if (leftover) {
      throw new Error(
        `unrecognized ${leftover[1]} form in ${file} — the ` +
          'mini-loader only strips "import ... from \'...\';" and ' +
          '"^export const|function|class" forms'
      );
    }
    loaded.push(stripped);
  }
  walk(PANEL_PATH);
  return loaded.join('\n');
}

vm.runInContext(loadPanelSource() + hook, sandbox);
const {
  coherenceToVerify,
  coherenceCompare,
  coherenceSortValue,
  coherenceType,
  filterCoherenceRows,
  nextCoherenceSort,
  coherenceFieldValue,
  coherenceLiveFields,
  coherenceIdentityFields,
  coherenceRawPairs,
  coherenceRawJson,
  coherencePopoverPosition,
  coherenceTriggerHtml,
  coherenceEntityLinkHtml,
  coherenceHasEntity,
  coherenceRowHtml,
  EedomusConfigPanel,
  coherenceDetailHtml,
  coherenceDetailAttempts,
  nextCoherenceExpanded,
  coherenceIsExpanded,
  coherenceExpandedRowId,
  coherenceExpandedRowHtml,
  coherenceRowExpansionHtml,
  POPOVER_FOCUSABLE_SELECTOR,
  coherenceHeadHtml,
  coherenceChipsHtml,
  coherenceChipHtml,
  COHERENCE_SIGNALS,
  COHERENCE_OK_SIGNAL,
  periphStatusText,
  coherenceStatusText,
  COHERENCE_COLUMNS,
  supervisionChartPoints,
  supervisionLinePath,
  supervisionBarRects,
  supervisionLineChartHtml,
  supervisionBarChartHtml,
  supervisionMetricCardHtml,
  supervisionFormatSeconds,
  supervisionFormatCount,
} = sandbox.__coherence;

// Fixture translator (CAP-3): the frozen FR catalog, identical
// interpolation semantics to the panel's t().
const FR = loadFrCatalog();
const t = catalogTranslator(FR);

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

// --- sort cycle: ascending -> descending -> neutral (response order) ---
assertEq(
  'cycle: 1st click ascending',
  nextCoherenceSort({ key: null, dir: null }, 'name'),
  { key: 'name', dir: 'asc' }
);
assertEq(
  'cycle: 2nd click descending',
  nextCoherenceSort({ key: 'name', dir: 'asc' }, 'name'),
  { key: 'name', dir: 'desc' }
);
assertEq(
  'cycle: 3rd click neutral',
  nextCoherenceSort({ key: 'name', dir: 'desc' }, 'name'),
  { key: null, dir: null }
);
assertEq(
  'cycle: other column restarts ascending',
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

// --- popover: living state fields (ticket 2.4) ---
const LIVE_ROW = {
  periph_id: '101',
  entity_id: 'sensor.salon',
  state: '21.5',
  usage_id: '96:3',
  parent_periph_id: '54',
  last_update: '2026-10-03T14:02:00',
};
assertEq(
  'live: full row projects every field',
  coherenceLiveFields(LIVE_ROW, t).map((f) => [f.label, f.value]),
  [
    ['Entité HA', 'sensor.salon'],
    ['Valeur courante', '21.5'],
    ['usage_id', '96:3'],
    ['Périphérique parent', '54'],
    ['Dernière mise à jour', '2026-10-03T14:02:00'],
  ]
);
assertEq(
  'live: null/empty values stay visible as null',
  coherenceLiveFields({ entity_id: 'sensor.x', state: null, usage_id: '' }, t),
  [
    { label: 'Entité HA', value: 'sensor.x', mono: true },
    { label: 'Valeur courante', value: null },
    { label: 'usage_id', value: null, mono: true },
    { label: 'Périphérique parent', value: null, mono: true },
    { label: 'Dernière mise à jour', value: null },
  ]
);
assertEq(
  'live: row without entity shows the no-entity text and no value',
  coherenceLiveFields({ entity_id: null, state: '21.5' }, t),
  [
    { label: 'Entité HA', value: 'aucune entité', mono: true },
    { label: 'Valeur courante', value: null },
    { label: 'usage_id', value: null, mono: true },
    { label: 'Périphérique parent', value: null, mono: true },
    { label: 'Dernière mise à jour', value: null },
  ]
);

// --- popover: mapping identity fields ---
assertEq(
  'identity: mapped row',
  coherenceIdentityFields({
    ha_entity: 'sensor',
    ha_subtype: 'temperature',
    justification: 'Unité température salon',
  }, t),
  [
    { label: 'ha_entity', value: 'sensor', mono: true },
    { label: 'ha_subtype', value: 'temperature', mono: true },
    { label: 'Justification', value: 'Unité température salon' },
  ]
);
assertEq(
  'identity: unmapped row keeps null fields',
  coherenceIdentityFields({}, t),
  [
    { label: 'ha_entity', value: null, mono: true },
    { label: 'ha_subtype', value: null, mono: true },
    { label: 'Justification', value: null },
  ]
);

// --- popover: raw API pairs ---
assertEq(
  'raw: sorted by key, nested values as compact JSON',
  coherenceRawPairs({ last_value: 42, name: 'Salon', raw: { a: 1 } }),
  [
    ['last_value', '42'],
    ['name', 'Salon'],
    ['raw', '{"a":1}'],
  ]
);
assertEq(
  'raw: null/undefined raw never throws, empty pairs',
  [coherenceRawPairs(null), coherenceRawPairs(undefined)],
  [[], []]
);
assertEq(
  'raw: scalar types stringify honestly',
  coherenceRawPairs({ flag: true, hole: null, text: 'x' }),
  [
    ['flag', 'true'],
    ['hole', 'null'],
    ['text', 'x'],
  ]
);

// --- popover: viewport-clamped positioning ---
assertEq(
  'position: anchors below the cell',
  coherencePopoverPosition(
    { left: 100, top: 200, bottom: 240 },
    { width: 380, height: 300 },
    { width: 1200, height: 800 }
  ),
  { left: 100, top: 248 }
);
assertEq(
  'position: flips above when there is more room there',
  coherencePopoverPosition(
    { left: 100, top: 400, bottom: 780 },
    { width: 380, height: 300 },
    { width: 1200, height: 800 }
  ),
  { left: 100, top: 92 }
);
assertEq(
  'position: clamps left when the cell is near the edge',
  coherencePopoverPosition(
    { left: 4, top: 200, bottom: 240 },
    { width: 380, height: 300 },
    { width: 1200, height: 800 }
  ),
  { left: 8, top: 248 }
);
assertEq(
  'position: clamps right when the popover would overflow',
  coherencePopoverPosition(
    { left: 1100, top: 200, bottom: 240 },
    { width: 380, height: 300 },
    { width: 1200, height: 800 }
  ),
  { left: 812, top: 248 }
);
assertEq(
  'position: clamps when the popover is taller than the viewport',
  coherencePopoverPosition(
    { left: 100, top: 10, bottom: 50 },
    { width: 380, height: 900 },
    { width: 1200, height: 400 }
  ),
  { left: 100, top: 8 }
);

// --- popover: shared value normalizer (ticket 2.4) ---
assertEq(
  'field value: null/undefined/empty -> null, rest -> String',
  [
    coherenceFieldValue(null),
    coherenceFieldValue(undefined),
    coherenceFieldValue(''),
    coherenceFieldValue(0),
    coherenceFieldValue(42),
    coherenceFieldValue('0'),
  ],
  [null, null, null, '0', '42', '0']
);

// --- popover: trigger markup (hostile periph_id) ---
const triggerHtml = coherenceTriggerHtml('"><script>&', false, null, t);
assertEq(
  'trigger: periph_id escaped in attribute, text and accessible name',
  [
    triggerHtml.includes(
      'data-coherence-popover="&quot;&gt;&lt;script&gt;&amp;"'
    ),
    triggerHtml.includes('<code>&quot;&gt;&lt;script&gt;&amp;</code>'),
    triggerHtml.includes(
      'aria-label="Détails du périphérique &quot;&gt;&lt;script&gt;&amp;"'
    ),
    triggerHtml.includes('aria-expanded="false"'),
    // Surface-neutral template: haspopup is set by the popover wiring
    // when it opens, never statically (the narrow side expands a row).
    !triggerHtml.includes('aria-haspopup'),
  ],
  [true, true, true, true, true]
);
assertEq(
  'trigger: expanded flag reflects the mobile extended row (2.5)',
  [
    coherenceTriggerHtml('101', true, null, t).includes('aria-expanded="true"'),
    coherenceTriggerHtml('101', true, null, t).includes(
      'aria-label="Détails du périphérique 101"'
    ),
    coherenceTriggerHtml('101', true, 'coherence-expanded-101', t).includes(
      'aria-controls="coherence-expanded-101"'
    ),
    // Documented default: no expansion arguments -> collapsed trigger.
    coherenceTriggerHtml('101', false, null, t).includes('aria-expanded="false"'),
    !coherenceTriggerHtml('101', false, null, t).includes('aria-controls'),
  ],
  [true, true, true, true, true]
);

// --- mobile expanded row (2.5): toggle semantics ---
assertEq(
  'expanded toggle: tap on a collapsed line opens it',
  nextCoherenceExpanded(null, '101'),
  '101'
);
assertEq(
  'expanded toggle: re-tap on the open line closes it',
  nextCoherenceExpanded('101', '101'),
  null
);
assertEq(
  'expanded toggle: tap on another line moves the extension',
  nextCoherenceExpanded('77', '101'),
  '101'
);
assertEq(
  'expanded toggle: null tap never opens',
  nextCoherenceExpanded('101', null),
  null
);

// --- popover: detail body (hostile values, edge rows) ---
const DETAIL_ROW = {
  periph_id: '101',
  name: 'Salon "Nord" <étage> & Co',
  entity_id: 'sensor.salon',
  state: '21.5',
  usage_id: '96:3',
  parent_periph_id: null,
  last_update: '2026-10-03T14:02:00',
  ha_entity: 'sensor',
  ha_subtype: 'temperature',
  justification: 'Unité « salon » <&>',
  error_message: 'Échec "API" <timeout> & retry',
  attempts: 'beaucoup',
  retry_after: '2026-10-03T15:00:00',
  raw: { name: 'a"b<c>&d', nested: { x: 1 } },
};
const detail = coherenceDetailHtml(DETAIL_ROW, t);
assertEq(
  'detail: hostile strings escape in every section',
  [
    detail.includes('Salon &quot;Nord&quot; &lt;étage&gt; &amp; Co'),
    detail.includes('Échec &quot;API&quot; &lt;timeout&gt; &amp; retry'),
    detail.includes('Unité « salon » &lt;&amp;&gt;'),
    detail.includes('a&quot;b&lt;c&gt;&amp;d'),
    detail.includes('{&quot;x&quot;:1}'),
  ],
  [true, true, true, true, true]
);
assertEq(
  'detail: actions and collapsed raw section',
  [
    detail.includes('Créer une règle'),
    // CAP-8: the disabled "Config HA" action became the active
    // "View in HA" link - the accessible name carries the entity.
    detail.includes('Voir dans HA'),
    detail.includes('data-entity-id="sensor.salon"'),
    detail.includes(
      'aria-label="Voir sensor.salon dans Home Assistant"'
    ),
    !detail.includes('bientôt disponible'),
    !detail.includes('<button class="row-action" type="button" disabled'),
    detail.includes('<details class="popover-raw">'),
    detail.includes("Champs bruts de l'API eedomus"),
    detail.includes('data-usage-id="96:3"'),
  ],
  [true, true, true, true, true, true, true, true, true]
);
assertEq(
  // 3.3 assumed the non-finite -> plural gap; the label now says
  // what the assertion actually pins (never NaN, always plural).
  'detail: non-numeric attempts take the plural form, never NaN',
  [
    detail.includes('(beaucoup tentatives)'),
    detail.includes('NaN'),
  ],
  [true, false]
);
const noEntityDetail = coherenceDetailHtml({
  periph_id: '12',
  name: '',
  entity_id: null,
  raw: null,
}, t);
assertEq(
  'detail: row without entity and empty name stays honest',
  [
    noEntityDetail.includes('aucune entité'),
    noEntityDetail.includes('inconnu'),
    noEntityDetail.includes('<span class="popover-name"></span>'),
    noEntityDetail.includes('<code class="popover-id">12</code>'),
    // Without an entity: no link and no navigation action (CAP-8).
    !noEntityDetail.includes('data-entity-id'),
    !noEntityDetail.includes('Voir dans HA'),
  ],
  [true, true, true, true, true, true]
);

// --- raw JSON block (UX run 3): fidelity under the sorted list ---
// Payload whose key order differs from the sorted one: the JSON must
// keep the original order, the list above it stays the sorted scan.
const ORDERED_RAW = { zebra: 1, alpha: 'x', mid: { deep: [1, 2] } };
const rawJsonText = coherenceRawJson(ORDERED_RAW);
assertEq(
  'raw json: indent 2, payload key order preserved',
  [
    rawJsonText.startsWith('{\n  "zebra": 1,'),
    rawJsonText.indexOf('zebra') < rawJsonText.indexOf('alpha'),
    rawJsonText.indexOf('alpha') < rawJsonText.indexOf('mid'),
    rawJsonText.includes('\n  "mid": {\n    "deep": [\n      1,\n      2\n    ]\n  }'),
  ],
  [true, true, true, true]
);
assertEq(
  'raw json: null and undefined render the honest "null"',
  [coherenceRawJson(null), coherenceRawJson(undefined)],
  ['null', 'null']
);
const jsonDetail = coherenceDetailHtml(
  Object.assign({}, DETAIL_ROW, { raw: ORDERED_RAW }),
  t
);
const rawBlock = jsonDetail.match(
  /<details class="popover-raw">([\s\S]*?)<\/details>/
)[1];
const listPart = rawBlock.split('<pre')[0];
const jsonPart = rawBlock.split('<pre')[1];
assertEq(
  'detail: JSON under the sorted list, keys in payload order',
  [
    rawBlock.indexOf('<dl>') < rawBlock.indexOf('<pre'),
    listPart.indexOf('alpha') < listPart.indexOf('zebra'),
    jsonPart.indexOf('zebra') < jsonPart.indexOf('alpha'),
    jsonPart.includes('&quot;zebra&quot;: 1'),
    // One escape pass only: quotes become entities, never double.
    !jsonDetail.includes('&amp;quot;'),
    !jsonDetail.includes('&amp;lt;'),
  ],
  [true, true, true, true, true, true]
);
assertEq(
  'detail: copy button and dedicated live region travel with the block',
  [
    rawBlock.includes('data-copy-json="1"'),
    rawBlock.includes('Copier le JSON'),
    rawBlock.includes('<p class="sr-only" id="copy-status-live" role="status">'),
    // Mobile parity is free: the expansion reuses coherenceDetailHtml.
    coherenceRowExpansionHtml(DETAIL_ROW, DETAIL_ROW.periph_id, true, t)
      .expansion.includes('data-copy-json="1"'),
    coherenceRowExpansionHtml(DETAIL_ROW, DETAIL_ROW.periph_id, true, t)
      .expansion.includes('copy-status-live'),
  ],
  [true, true, true, true, true]
);
assertEq(
  'detail: null payload renders the honest JSON "null"',
  coherenceDetailHtml({ periph_id: '12', name: '', raw: null }, t)
    .includes('<pre class="raw-json"><code>null</code></pre>'),
  true
);

// --- entity link (2.6, CAP-8): markup, hostile and null cases ---
assertEq(
  'entity link: null/undefined/empty stays the inert no-entity text',
  [
    coherenceEntityLinkHtml(null, t),
    coherenceEntityLinkHtml(undefined, t),
    coherenceEntityLinkHtml('', t),
  ],
  [
    '<em>aucune entité</em>',
    '<em>aucune entité</em>',
    '<em>aucune entité</em>',
  ]
);
const linkHtml = coherenceEntityLinkHtml('sensor.salon', t);
assertEq(
  'entity link: inline text link carrying the entity label',
  [
    linkHtml.includes('<a class="entity-link"'),
    linkHtml.includes('href="#"'),
    linkHtml.includes('data-entity-id="sensor.salon"'),
    linkHtml.includes('>sensor.salon</a>'),
    // Action-bearing accessible name, mirroring the detail's
    // « Voir dans HA » — the visible text stays the entity id.
    linkHtml.includes('aria-label="Voir sensor.salon dans Home Assistant"'),
    !linkHtml.includes('<button'),
  ],
  [true, true, true, true, true, true]
);
const hostileLink = coherenceEntityLinkHtml('"><script>&', t);
assertEq(
  'entity link: hostile entity_id escapes in attribute and text',
  [
    hostileLink.includes('data-entity-id="&quot;&gt;&lt;script&gt;&amp;"'),
    hostileLink.includes('>&quot;&gt;&lt;script&gt;&amp;</a>'),
  ],
  [true, true]
);

// --- predicate parity (2.6): one no-entity predicate, both surfaces ---
assertEq(
  'predicate: whitespace-only id is inert on both surfaces',
  [
    coherenceHasEntity('   '),
    coherenceEntityLinkHtml('   ', t),
    coherenceDetailHtml({ periph_id: '5', name: 'X', entity_id: '   ' }, t)
      .includes('data-entity-id'),
  ],
  [false, '<em>aucune entité</em>', false]
);

// --- composed row (2.6): the entity cell on both sides of the mapping ---
const mappedRow = coherenceRowHtml(ROWS[0], null, false, t);
const inertRow = coherenceRowHtml(ROWS[1], null, false, t);
assertEq(
  'row: mapped row carries the entity link, null-entity row stays inert',
  [
    mappedRow.includes('<td class="ha-entity" data-label="Entité HA">'),
    mappedRow.includes('data-entity-id="sensor.salon"'),
    mappedRow.includes(
      'aria-label="Voir sensor.salon dans Home Assistant"'
    ),
    !mappedRow.includes('<em>aucune entité</em>'),
    inertRow.includes('<em>aucune entité</em>'),
    !inertRow.includes('data-entity-id'),
  ],
  [true, true, true, true, true, true]
);

// --- hostile entity_id on the detail button path (2.6, CAP-8) ---
const hostileDetail = coherenceDetailHtml({
  periph_id: '5',
  name: 'X',
  entity_id: '"><script>&',
}, t);
assertEq(
  'detail: hostile entity_id escapes in the action attribute and name',
  [
    hostileDetail.includes('data-entity-id="&quot;&gt;&lt;script&gt;&amp;"'),
    hostileDetail.includes(
      'aria-label="Voir &quot;&gt;&lt;script&gt;&amp; dans Home Assistant"'
    ),
  ],
  [true, true]
);

// --- hass-more-info dispatch (2.6, CAP-8) ---
const panel = new EedomusConfigPanel();
const dispatched = [];
panel.dispatchEvent = (ev) => {
  dispatched.push(ev);
  return true;
};
let prevented = 0;
let stopped = 0;
const entityLinkStub = { dataset: { entityId: 'sensor.salon' } };
panel._onClick({
  target: {
    closest: (sel) => (sel === '[data-entity-id]' ? entityLinkStub : null),
  },
  preventDefault: () => {
    prevented += 1;
  },
  stopPropagation: () => {
    stopped += 1;
  },
});
assertEq(
  'dispatch: activating the entity link emits hass-more-info',
  [
    prevented,
    stopped,
    dispatched.length,
    dispatched[0].type,
    dispatched[0].detail,
    dispatched[0].bubbles,
    dispatched[0].composed,
  ],
  [1, 1, 1, 'hass-more-info', { entityId: 'sensor.salon' }, true, true]
);
panel._openEntityMoreInfo('   ');
assertEq(
  'dispatch: inert id never emits (predicate parity)',
  dispatched.length,
  1
);

// --- mobile expanded row (2.5): predicate + composed emission ---
assertEq(
  'expansion predicate: narrow viewport and matching id, nothing else',
  [
    coherenceIsExpanded(DETAIL_ROW, '101', true),
    coherenceIsExpanded(DETAIL_ROW, '101', false),
    coherenceIsExpanded(DETAIL_ROW, '77', true),
    coherenceIsExpanded(DETAIL_ROW, null, true),
  ],
  [true, false, false, false]
);
const expandedOut = coherenceRowExpansionHtml(DETAIL_ROW, '101', true, t);
assertEq(
  'expansion: composed output emits the full surface when expanded',
  [
    expandedOut.expanded,
    expandedOut.rowClass.includes('coherence-row-expanded'),
    expandedOut.trigger.includes('aria-expanded="true"'),
    expandedOut.trigger.includes('aria-controls="coherence-expanded-101"'),
    expandedOut.expansion.includes('coherence-expanded-row'),
    expandedOut.expansion.includes('id="coherence-expanded-101"'),
    // Content parity: the shared detail body inside the expansion,
    // spanning every column of COHERENCE_COLUMNS.
    expandedOut.expansion.includes(
      '<div class="coherence-expanded-body">'
    ),
    expandedOut.expansion.includes('colspan="5"'),
    expandedOut.expansion.includes('Salon &quot;Nord&quot;'),
    expandedOut.expansion.includes('Créer une règle'),
  ],
  [true, true, true, true, true, true, true, true, true, true]
);
const otherIdOut = coherenceRowExpansionHtml(DETAIL_ROW, '77', true, t);
const wideOut = coherenceRowExpansionHtml(DETAIL_ROW, '101', false, t);
assertEq(
  'expansion: nothing emitted when not expanded (other id or wide)',
  [
    otherIdOut.expanded,
    otherIdOut.rowClass,
    otherIdOut.expansion,
    otherIdOut.trigger.includes('aria-expanded="false"'),
    !otherIdOut.trigger.includes('aria-controls'),
    wideOut.expanded,
    wideOut.rowClass,
    wideOut.expansion,
  ],
  [false, '', '', true, true, false, '', '']
);
// Hostile periph_id: the predicate and the aria-controls target use
// the same id on both sides — an id with quotes or angle brackets
// expands exactly like the popover opens.
const HOSTILE_ID = '"><s>&';
const hostileOut = coherenceRowExpansionHtml(
  { periph_id: HOSTILE_ID },
  HOSTILE_ID,
  true,
  t
);
assertEq(
  'expansion: hostile periph_id matches and escapes on both sides',
  [
    coherenceIsExpanded({ periph_id: HOSTILE_ID }, HOSTILE_ID, true),
    hostileOut.trigger.includes(
      'aria-controls="coherence-expanded-&quot;&gt;&lt;s&gt;&amp;"'
    ),
    hostileOut.expansion.includes(
      'id="coherence-expanded-&quot;&gt;&lt;s&gt;&amp;"'
    ),
    hostileOut.expansion.includes('coherence-expanded-row'),
  ],
  [true, true, true, true]
);

// --- popover: attempts plural guard ---
// The catalog splits the singular/plural forms (CAP-3 review): 1 takes
// attempts_one, everything else (non-numeric included) attempts_other.
assertEq(
  'attempts: finite count > 1 pluralizes',
  coherenceDetailAttempts(3, t),
  ' (3 tentatives)'
);
assertEq(
  'attempts: 1 stays singular',
  coherenceDetailAttempts(1, t),
  ' (1 tentative)'
);
assertEq(
  'attempts: non-numeric takes the plural, never NaN',
  coherenceDetailAttempts('beaucoup', t),
  ' (beaucoup tentatives)'
);

// --- popover: focus trap selector excludes disabled uniformly ---
assertEq(
  'selector: no disabled control is a trap stop',
  [
    POPOVER_FOCUSABLE_SELECTOR.includes('button:not([disabled])'),
    POPOVER_FOCUSABLE_SELECTOR.includes('input:not([disabled])'),
    POPOVER_FOCUSABLE_SELECTOR.includes('select:not([disabled])'),
    POPOVER_FOCUSABLE_SELECTOR.includes('textarea:not([disabled])'),
    POPOVER_FOCUSABLE_SELECTOR.includes('summary'),
  ],
  [true, true, true, true, true]
);

// --- shared head generator (sweep): table and skeleton, same markup ---
const NEUTRAL_SORT = { key: null, dir: null };
const neutralHead = coherenceHeadHtml(NEUTRAL_SORT, t);
assertEq(
  'head: neutral sort renders the five columns as plain sort buttons',
  [
    (neutralHead.match(/<th scope="col" aria-sort="none">/g) || []).length,
    ['periph_id', 'name', 'entity_id', 'type', 'status'].every((key) =>
      neutralHead.includes(`data-sort-key="${key}"`)
    ),
    ['periph_id', 'Nom', 'Entité HA', 'Type / sous-type', 'Statut'].every(
      (label) => neutralHead.includes(`Trier par ${label}"`)
    ),
    !neutralHead.includes('sort-arrow'),
    !neutralHead.includes('actuellement'),
  ],
  [5, true, true, true, true]
);
const sortedHead = coherenceHeadHtml({ key: 'name', dir: 'desc' }, t);
assertEq(
  'head: sorted column carries aria-sort, arrow and state label',
  [
    (sortedHead.match(/aria-sort="descending"/g) || []).length,
    (sortedHead.match(/aria-sort="none"/g) || []).length,
    sortedHead.includes('aria-label="Trier par Nom, actuellement décroissant"'),
    sortedHead.includes('sort-arrow'),
    !sortedHead.includes('actuellement croissant'),
  ],
  [1, 4, true, true, true]
);

// --- status-line texts (sweep): render and debounce share one helper ---
assertEq(
  'periph status: plain count, then filter label with its own count',
  [
    periphStatusText(63, 63, false, t),
    periphStatusText(63, 12, true, t),
  ],
  [
    '63 périphériques',
    '63 périphériques — filtre « Périphériques touchés » actif : 12 résultats',
  ]
);
assertEq(
  'periph status: a count of 1 takes the singular form (one/other split)',
  [periphStatusText(1, 1, false, t), periphStatusText(1, 1, true, t)],
  [
    '1 périphérique',
    '1 périphérique — filtre « Périphériques touchés » actif : 1 résultat',
  ]
);
assertEq(
  'coherence status: count, view label, no-result and positive empty',
  [
    coherenceStatusText(165, '', 'all', t),
    coherenceStatusText(4, '', 'to_verify', t),
    coherenceStatusText(0, 'zzz', 'all', t),
    coherenceStatusText(0, '', 'to_verify', t),
  ],
  [
    '165 périphériques',
    '4 périphériques — vue « À vérifier » active : 4 résultats',
    'Aucun périphérique ne correspond à “zzz”.',
    'Tout est cohérent. Aucun périphérique à vérifier.',
  ]
);
assertEq(
  'coherence status: a count of 1 takes the singular form (one/other split)',
  coherenceStatusText(1, '', 'all', t),
  '1 périphérique'
);

// --- keystroke debounce wiring (sweep): one announcement per burst ---
// The visible count updates on every keystroke; only the sr-only live
// region waits for the captured 300 ms timer.
const announcePanel = new EedomusConfigPanel();
// CAP-3: the render paths go through t() — the instance carries the FR
// fixture catalog, exactly what set hass loads in production.
announcePanel._strings = FR;
announcePanel._stringsLocale = 'fr';
const liveLog = [];
const liveEl = { id: 'coherence-status-live' };
Object.defineProperty(liveEl, 'textContent', {
  get: () => liveLog[liveLog.length - 1] || '',
  set: (value) => {
    liveLog.push(value);
  },
});
const coherenceEls = {
  'coherence-status': { id: 'coherence-status', textContent: '' },
  'coherence-status-live': liveEl,
  'coherence-body': { id: 'coherence-body', innerHTML: '' },
};
announcePanel.shadowRoot = {
  getElementById: (id) => coherenceEls[id] || null,
  querySelector: () => null,
};
announcePanel._tab = 'coherence';
announcePanel._coherence = ROWS.slice();
announcePanel._coherenceSearch = '';
announcePanel._coherenceView = 'all';
announcePanel._coherenceSort = { key: null, dir: null };
announcePanel._onInput({ target: { id: 'coherence-search', value: 'sal' } });
assertEq(
  'debounce: keystroke schedules one timer, visible count immediate',
  [
    sandboxTimers.length,
    sandboxTimers[0].delay,
    coherenceEls['coherence-status'].textContent,
    liveLog,
  ],
  [1, 300, '1 périphérique', []]
);
announcePanel._onInput({ target: { id: 'coherence-search', value: 'salon' } });
assertEq(
  'debounce: next keystroke cancels the pending timer, live stays quiet',
  [
    sandboxTimers.length,
    sandboxCleared,
    liveLog,
    announcePanel._statusAnnounceTimers['coherence-status-live'],
  ],
  [2, [1], [], 2]
);
sandboxTimers[1].fn();
assertEq(
  'debounce: flush announces exactly once with the filtered count',
  [
    liveLog,
    announcePanel._statusAnnounceTimers['coherence-status-live'],
  ],
  [['1 périphérique'], undefined]
);
announcePanel._onInput({ target: { id: 'coherence-search', value: 'sal' } });
announcePanel._coherenceSortBy('name');
assertEq(
  'debounce: an immediate announce cancels the pending timer',
  [
    announcePanel._statusAnnounceTimers['coherence-status-live'],
    sandboxCleared[sandboxCleared.length - 1],
    sandboxTimers.length,
    liveLog[liveLog.length - 1],
  ],
  [undefined, 3, 3, '1 périphérique']
);

// --- skeleton (sweep): shared head, inert, derived colspan ---
const skeleton = announcePanel._renderCoherenceSkeleton();
assertEq(
  'skeleton: inert, neutral shared head, labels and colspan derived',
  [
    skeleton.includes('inert'),
    (skeleton.match(/aria-sort="none"/g) || []).length,
    !skeleton.includes('sort-arrow'),
    COHERENCE_COLUMNS.every((col) => skeleton.includes(t(col.labelKey))),
    skeleton.includes(`colspan="${COHERENCE_COLUMNS.length}"`),
  ],
  [true, 5, true, true, true]
);

// --- chips (verification hole, sweep): every signal, one chip -----
// The composed row never asserted the chips themselves — the main
// visible output of the tab could degrade with the suite green.
const CHIP_LABELS = {
  sans_entite: 'sans entité HA',
  douteux: 'mapping douteux',
  regle_active: 'règle active',
  en_erreur: 'import en reprise',
};
for (const signal of Object.keys(COHERENCE_SIGNALS)) {
  const chip = coherenceChipHtml(signal, { signals: [signal] }, t);
  assertEq(
    `chip: signal ${signal} renders its class, icon and catalog label`,
    [
      chip.includes(`class="coherence-chip coherence-chip-${signal}"`),
      chip.includes('<svg'),
      chip.includes(CHIP_LABELS[signal]),
    ],
    [true, true, true]
  );
}
assertEq(
  'chip: the label set matches the backend signal contract',
  Object.keys(COHERENCE_SIGNALS),
  ['sans_entite', 'douteux', 'regle_active', 'en_erreur']
);
const coherentChip = coherenceChipsHtml({ signals: [] }, t);
assertEq(
  'chip: a signal-less row renders the coherent fallback chip',
  [
    coherentChip.includes('coherence-chip-coherent'),
    coherentChip.includes('cohérent'),
    coherentChip.includes('<svg'),
  ],
  [true, true, true]
);
// Apostrophe-free message: escapeHtml turns ' into &#39;, and the
// point here is the truncation and the title, not the escaping
// (covered by the hostile-value tests above).
const LONG_ERROR =
  'Échec import historique : limite de débit API atteinte';
const erroredChip = coherenceChipHtml(
  'en_erreur',
  { signals: ['en_erreur'], error_message: LONG_ERROR },
  t
);
assertEq(
  'chip: en_erreur with a message carries the retry label, truncated detail, full title',
  [
    erroredChip.includes('import en reprise : '),
    erroredChip.includes(`${LONG_ERROR.slice(0, 39)}…`),
    erroredChip.includes(`title="${LONG_ERROR}"`),
  ],
  [true, true, true]
);
const unknownChip = coherenceChipHtml('signal_inconnu', {}, t);
assertEq(
  'chip: an unknown signal string keeps a neutral chip with the raw value',
  [
    unknownChip.includes('coherence-chip-unknown'),
    unknownChip.includes('signal_inconnu'),
    !unknownChip.includes('<svg'),
  ],
  [true, true, true]
);

// --- tap dispatch (verification hole, sweep): narrow vs wide --------
// matchMedia is stubbed: the same tap routes to the expanded row
// under the breakpoint and to the popover on the wide side.
const dispatchMedia = {
  matches: false,
  addEventListener() {},
  removeEventListener() {},
};
sandbox.window.matchMedia = () => dispatchMedia;
const dispatchPanel = new EedomusConfigPanel();
const expandedCalls = [];
const popoverCalls = [];
dispatchPanel._toggleCoherenceExpanded = (id) => {
  expandedCalls.push(id);
};
dispatchPanel._openCoherencePopover = (trigger, opts) => {
  popoverCalls.push([trigger, opts]);
};
const dispatchTrigger = { dataset: { coherencePopover: '101' } };
const dispatchClick = () => dispatchPanel._onClick({
  target: {
    closest: (sel) =>
      sel === '[data-coherence-popover]' ? dispatchTrigger : null,
  },
});
dispatchMedia.matches = true;
dispatchClick();
assertEq(
  'dispatch: a tap under the breakpoint expands the row, never the popover',
  [expandedCalls, popoverCalls],
  [['101'], []]
);
dispatchMedia.matches = false;
dispatchClick();
assertEq(
  'dispatch: a tap on the wide side opens the popover, focused',
  [
    expandedCalls,
    popoverCalls.length,
    popoverCalls[0][0] === dispatchTrigger,
    popoverCalls[0][1],
  ],
  [['101'], 1, true, { focusPopover: true }]
);
dispatchMedia.matches = false;
delete sandbox.window.matchMedia;

// --- render teardown (verification hole, sweep): popover + expansion
// The _closeCoherencePopover of every reshuffle and the eviction of
// an expansion absent from the filtered rows had no witness.
const teardownPanel = new EedomusConfigPanel();
teardownPanel._strings = FR;
teardownPanel._stringsLocale = 'fr';
const teardownEls = {
  'coherence-status': { id: 'coherence-status', textContent: '' },
  'coherence-status-live': { id: 'coherence-status-live', textContent: '' },
  'coherence-body': { id: 'coherence-body', innerHTML: '' },
};
const removedDoc = [];
const removedRoot = [];
teardownPanel.shadowRoot = {
  getElementById: (id) => teardownEls[id] || null,
  querySelector: () => null,
  removeEventListener: (type, fn) => {
    removedRoot.push([type, fn]);
  },
  activeElement: null,
};
let popRemoved = 0;
const teardownPop = {
  contains: () => false,
  remove: () => {
    popRemoved += 1;
  },
};
const teardownTrigger = { dataset: {}, setAttribute() {}, removeAttribute() {} };
const teardownDismiss = () => {};
const teardownFocusOut = () => {};
teardownPanel._coherencePopover = teardownPop;
teardownPanel._coherencePopoverTrigger = teardownTrigger;
teardownPanel._coherenceDismiss = teardownDismiss;
teardownPanel._coherenceFocusOut = teardownFocusOut;
teardownPanel._tab = 'coherence';
teardownPanel._coherence = ROWS.slice();
teardownPanel._coherenceExpandedId = '12'; // filtered out below
teardownPanel._coherenceSearch = 'sal'; // matches only periph 101
const savedTeardownDoc = sandbox.document;
sandbox.document = {
  removeEventListener: (type, fn) => {
    removedDoc.push([type, fn]);
  },
};
teardownPanel._renderCoherenceTable();
if (savedTeardownDoc === undefined) {
  delete sandbox.document;
} else {
  sandbox.document = savedTeardownDoc;
}
assertEq(
  'teardown: any reshuffle closes the popover and removes its listeners',
  [
    popRemoved,
    teardownPanel._coherencePopover,
    removedDoc,
    removedRoot,
  ],
  [
    1,
    null,
    [
      ['click', teardownDismiss],
      ['scroll', teardownDismiss],
    ],
    [['focusout', teardownFocusOut]],
  ]
);
assertEq(
  'teardown: an expansion absent from the filtered rows is evicted',
  [
    teardownPanel._coherenceExpandedId,
    teardownEls['coherence-status'].textContent,
    teardownEls['coherence-body'].innerHTML.includes('data-coherence-popover="101"'),
  ],
  [null, '1 périphérique', true]
);

// --- periphs typing debounce (verification hole, sweep) ------------
// Mirror of the coherence case: the visible count is immediate, only
// the live-region announcement waits for the captured 300 ms timer.
const periphDebouncePanel = new EedomusConfigPanel();
periphDebouncePanel._strings = FR;
periphDebouncePanel._stringsLocale = 'fr';
const periphDebounceLive = [];
const periphLiveEl = { id: 'periph-status-live' };
Object.defineProperty(periphLiveEl, 'textContent', {
  get: () =>
    periphDebounceLive[periphDebounceLive.length - 1] || '',
  set: (value) => {
    periphDebounceLive.push(value);
  },
});
const periphDebounceEls = {
  'periph-list': { id: 'periph-list', innerHTML: '' },
  'periph-status': { id: 'periph-status', textContent: '' },
  'periph-status-live': periphLiveEl,
};
periphDebouncePanel.shadowRoot = {
  getElementById: (id) => periphDebounceEls[id] || null,
  querySelector: () => null,
};
periphDebouncePanel._tab = 'peripheriques';
periphDebouncePanel._periphs = [
  { periph_id: '101', name: 'Salon', usage_id: '1', entity_id: 'sensor.s' },
  { periph_id: '12', name: 'Cave', usage_id: '2', entity_id: null },
];
const periphTimerBase = sandboxTimers.length;
periphDebouncePanel._onInput({ target: { id: 'periph-search', value: 'sal' } });
const periphFirstHandle =
  periphDebouncePanel._statusAnnounceTimers['periph-status-live'];
assertEq(
  'periphs debounce: one 300ms timer scheduled, visible count immediate',
  [
    sandboxTimers.length - periphTimerBase,
    sandboxTimers[sandboxTimers.length - 1].delay,
    periphDebounceEls['periph-status'].textContent,
    periphDebounceLive,
  ],
  [1, 300, '2 périphériques', []]
);
periphDebouncePanel._onInput({ target: { id: 'periph-search', value: 'salon' } });
assertEq(
  'periphs debounce: next keystroke replaces the pending timer, live quiet',
  [
    sandboxTimers.length - periphTimerBase,
    periphDebouncePanel._statusAnnounceTimers['periph-status-live'],
    periphDebounceLive,
    sandboxCleared[sandboxCleared.length - 1] === periphFirstHandle,
  ],
  [2, periphFirstHandle + 1, [], true]
);
sandboxTimers[sandboxTimers.length - 1].fn();
assertEq(
  'periphs debounce: flush announces exactly once after the pause',
  periphDebounceLive,
  ['2 périphériques']
);

// --- hover intent races (sweep): sweep + narrow crossing ----------
// The dispatch test cached the narrow media query on the module - the
// same stub object drives both surfaces here.
const hoverQuery = {
  matches: true,
  addEventListener() {},
  removeEventListener() {},
};
sandbox.window.matchMedia = (query) =>
  query.indexOf('hover') !== -1 ? hoverQuery : dispatchMedia;
dispatchMedia.matches = false;
const hoverPanel = new EedomusConfigPanel();
hoverPanel._tab = 'coherence';
hoverPanel._coherence = ROWS.slice();
const hoverOpened = [];
hoverPanel._openCoherencePopover = (trigger, opts) => {
  hoverOpened.push([trigger, opts]);
};
const hoverTriggerA = {
  dataset: { coherencePopover: '101' },
  closest: (sel) =>
    sel === '[data-coherence-popover]' ? hoverTriggerA : null,
};
const hoverTriggerB = {
  dataset: { coherencePopover: '12' },
  closest: (sel) =>
    sel === '[data-coherence-popover]' ? hoverTriggerB : null,
};
// The sweep race: a pending leave-timer from the previous popover
// must die with the new intent - its close would otherwise cancel
// this very intent and no popover would ever open.
hoverPanel._coherenceLeaveTimer = 77;
hoverPanel._onCoherenceMouseOver({ target: hoverTriggerA });
assertEq(
  'hover: a new intent cancels the pending leave-timer',
  [hoverPanel._coherenceLeaveTimer, sandboxTimers.length > 0],
  [null, true]
);
const intentTimer =
  sandboxTimers[sandboxTimers.length - 1];
assertEq(
  'hover: the intent waits ~250ms before opening',
  intentTimer.delay,
  250
);
intentTimer.fn();
assertEq(
  'hover: the intent opens the popover on the wide side, unfocused',
  [hoverOpened.length, hoverOpened[0][0] === hoverTriggerA, hoverOpened[0][1]],
  [1, true, { focusPopover: false, byHover: true }]
);
// Viewport crossed during the intent window: the popover is a
// wide-only surface, the timer must not open it under the breakpoint.
hoverPanel._onCoherenceMouseOver({ target: hoverTriggerB });
dispatchMedia.matches = true;
sandboxTimers[sandboxTimers.length - 1].fn();
assertEq(
  'hover: an intent that outlives the breakpoint crossing never opens',
  [hoverOpened.length, hoverPanel._coherenceHoverTimer],
  [1, null]
);
hoverQuery.matches = false;
dispatchMedia.matches = false;
delete sandbox.window.matchMedia;

// --- breakpoint crossing (sweep): popover down, expansion up -------
const narrowPanel = new EedomusConfigPanel();
let narrowClosed = 0;
narrowPanel._closeCoherencePopover = () => {
  narrowClosed += 1;
};
narrowPanel._coherenceExpandedId = '101';
narrowPanel._onCoherenceBreakpoint({ matches: true });
assertEq(
  'breakpoint: entering narrow closes the popover, expansion survives',
  [narrowClosed, narrowPanel._coherenceExpandedId],
  [1, '101']
);
const widePanel = new EedomusConfigPanel();
const wideRenders = [];
widePanel._closeCoherencePopover = () => {};
widePanel._renderCoherenceTable = () => {
  wideRenders.push(1);
};
widePanel._coherenceTriggerFor = () => null;
widePanel._tab = 'coherence';
widePanel.shadowRoot = {
  getElementById: () => null,
  activeElement: null,
};
widePanel._coherenceExpandedId = '101';
widePanel._onCoherenceBreakpoint({ matches: false });
assertEq(
  'breakpoint: entering wide drops the expansion and re-renders',
  [widePanel._coherenceExpandedId, wideRenders.length],
  [null, 1]
);

// --- "Show all" focus restoration (sweep): the witness -----------
// The re-render replaces the coherence body (the button lives in it) -
// focus must land on the view toggle, the control that owns the state.
const showAllPanel = new EedomusConfigPanel();
showAllPanel._strings = FR;
showAllPanel._stringsLocale = 'fr';
const showAllFocusLog = [];
const showAllViewBtn = {
  setAttribute() {},
  querySelector: () => null,
  focus() {
    showAllFocusLog.push(1);
  },
};
const showAllEls = {
  'coherence-status': { id: 'coherence-status', textContent: '' },
  'coherence-status-live': { id: 'coherence-status-live', textContent: '' },
  'coherence-body': { id: 'coherence-body', innerHTML: '' },
};
showAllPanel.shadowRoot = {
  getElementById: (id) => showAllEls[id] || null,
  querySelector: (sel) =>
    sel === '[data-coherence-view]' ? showAllViewBtn : null,
};
showAllPanel._tab = 'coherence';
showAllPanel._coherence = ROWS.slice();
showAllPanel._coherenceView = 'to_verify';
showAllPanel._coherenceExpandedId = null;
showAllPanel._onClick({
  target: {
    closest: (sel) => (sel === '[data-coherence-show-all]' ? {} : null),
  },
});
assertEq(
  'show all: the re-render restores focus on the view toggle',
  [showAllFocusLog.length, showAllPanel._coherenceView],
  [1, 'all']
);

// --- status/banner instance rendering (3.3 review findings) ------
// The stored statuses resolve through t() at display time, twice:
// the stored key (or raw message) and the ts descriptor inside it.
const statusPanel = new EedomusConfigPanel();
statusPanel._strings = FR;
statusPanel._stringsLocale = 'fr';
statusPanel._historyStatus = { key: 'panel.historique.restore.progress' };
assertEq(
  'history status: a stored key resolves through t()',
  statusPanel._historyStatusText(),
  'Sauvegarde… puis Application…'
);
statusPanel._historyStatus = {
  key: 'panel.historique.restore.success',
  ts: '2026-10-03 09:19',
};
assertEq(
  'history status: a raw ts passes through t() unchanged (key-or-message)',
  statusPanel._historyStatusText(),
  'Version du 2026-10-03 09:19 restaurée. Le mapping remplacé est archivé.'
);
statusPanel._historyStatus = {
  key: 'panel.historique.restore.success',
  ts: 'panel.common.unknown_date',
};
assertEq(
  'history status: a stored ts key resolves too (double resolution)',
  statusPanel._historyStatusText(),
  'Version du date inconnue restaurée. Le mapping remplacé est archivé.'
);
statusPanel._historyStatus = null;
assertEq(
  'history status: no stored status renders the empty string',
  statusPanel._historyStatusText(),
  ''
);
const rulesStatusEl = { id: 'rules-status', textContent: '' };
statusPanel.shadowRoot = {
  getElementById: (id) => (id === 'rules-status' ? rulesStatusEl : null),
};
statusPanel._validation = { valid: false, message: '' };
statusPanel._rulesStatus = '';
statusPanel._saveState = { applied: true };
statusPanel._updateRulesStatus();
assertEq(
  'rules status: the plain applied descriptor resolves',
  rulesStatusEl.textContent,
  'Configuration appliquée.'
);
statusPanel._saveState = {
  applied: {
    entity_id: {
      key: 'panel.regles.status.rule_applied_entity_fallback',
      params: { rule: '24' },
    },
    unit: { key: 'panel.regles.status.rule_applied_unit_fallback' },
  },
};
statusPanel._updateRulesStatus();
assertEq(
  'rules status: fallback descriptors resolve through t() (resolveApplied)',
  rulesStatusEl.textContent,
  'Règle appliquée. usage_id 24 est maintenant en sa nouvelle valeur.'
);
statusPanel._saveState = { error: 'panel.common.unknown_error' };
statusPanel._updateRulesStatus();
assertEq(
  'rules status: an error key resolves through t()',
  rulesStatusEl.textContent,
  'Échec de la sauvegarde : erreur inconnue. Le formulaire conserve vos ' +
    'modifications.'
);
statusPanel._saveState = { error: 'Validation failed' };
statusPanel._updateRulesStatus();
assertEq(
  'rules status: a raw error message passes through t() unchanged',
  rulesStatusEl.textContent,
  'Échec de la sauvegarde : Validation failed. Le formulaire conserve ' +
    'vos modifications.'
);

// --- Supervision tab (CAP-9): chart math, render states, link -------
// The pure chart helpers scale inside the fixed viewBox; the instance
// renders drive the FR catalog through the real mixin methods.
assertEq(
  'supervision: an empty series yields no points',
  supervisionChartPoints([]),
  []
);
const supPoints = supervisionChartPoints([1, 2, 3]);
assertEq(
  'supervision: an increasing series climbs (x up, y down)',
  [
    supPoints.length,
    supPoints[0][0] < supPoints[1][0],
    supPoints[0][1] > supPoints[1][1],
    supPoints[1][1] > supPoints[2][1],
  ],
  [3, true, true, true]
);
assertEq(
  'supervision: points stay inside the viewBox',
  supPoints.every(
    (p) => p[0] >= 0 && p[0] <= 300 && p[1] >= 0 && p[1] <= 120
  ),
  true
);
assertEq(
  'supervision: a flat series still draws (never a zero sliver)',
  supervisionChartPoints([4, 4, 4]).length,
  3
);
assertEq(
  'supervision: the line path joins the points',
  supervisionLinePath([[0, 0], [10, 10], [20, 5]]),
  'M0,0 L10,10 L20,5'
);
const supBars = supervisionBarRects([1, 2, 3]);
assertEq(
  'supervision: bars scale against zero (last tallest, y smallest)',
  [
    supBars.length,
    supBars[2].height > supBars[0].height,
    supBars[2].y < supBars[0].y,
  ],
  [3, true, true]
);
assertEq(
  'supervision: value formatting (bare, with unit, missing)',
  [
    supervisionFormatSeconds(1.5),
    supervisionFormatSeconds(1.5, true),
    supervisionFormatCount(12.4),
    supervisionFormatSeconds(undefined),
  ],
  ['1.500', '1.500 s', '12', '—']
);
assertEq(
  'supervision: the line chart emits a themed svg, nothing on empty',
  [
    supervisionLineChartHtml([1, 2]).includes('<svg'),
    supervisionLineChartHtml([1, 2]).includes('var(--primary-color)'),
    supervisionLineChartHtml([]),
  ],
  [true, true, '']
);

const supPanel = new EedomusConfigPanel();
supPanel._strings = FR;
supPanel._stringsLocale = 'fr';
supPanel._tab = 'supervision';
// First render of the tab: card-shaped skeletons, loading announced,
// never a catalog key as text.
const supSkeletonHtml = supPanel._renderSupervisionTab();
assertEq(
  'supervision: first render is card skeletons + loading status',
  [
    supSkeletonHtml.includes('metric-skeleton'),
    (supSkeletonHtml.match(/metric-skeleton/g) || []).length,
    supSkeletonHtml.includes('Chargement de la supervision…'),
    supSkeletonHtml.includes('panel.'),
  ],
  [true, 3, true, false]
);
// Error state: alert + Retry, never a half-loaded card.
supPanel._metricsError = 'panel.common.command_refused';
const supErrorHtml = supPanel._renderSupervisionTab();
assertEq(
  'supervision: a ws error renders the alert + Retry button',
  [
    supErrorHtml.includes('role="alert"'),
    supErrorHtml.includes('Impossible de charger les métriques'),
    supErrorHtml.includes('data-retry="metrics"'),
  ],
  [true, true, true]
);
// Loaded state: cards with charts AND the textual equivalents — the
// chart is never the sole carrier.
supPanel._metricsError = null;
supPanel._metrics = {
  boxes: [
    {
      entry_id: 'E1',
      name: 'Salon',
      periphs_dynamic: 6,
      cycles: [
        {
          ts: '2026-10-03T09:00:00',
          refresh_time: 2.5,
          api_time: 1.25,
          api_calls: 3,
          periphs_total: 164,
          periphs_dynamic: 6,
        },
        {
          ts: '2026-10-03T09:05:00',
          refresh_time: 2.1,
          api_time: 1.1,
          api_calls: 2,
          periphs_total: 165,
          periphs_dynamic: 6,
        },
      ],
    },
  ],
};
const supCardsHtml = supPanel._renderSupervisionTab();
assertEq(
  'supervision: cards render with charts and textual equivalents',
  [
    supCardsHtml.includes('metric-card'),
    supCardsHtml.includes('<svg'),
    supCardsHtml.includes(
      'Dernier cycle : 2.100 s au total, 1.100 s sur l&#39;API.'
    ),
    supCardsHtml.includes('165 périphériques, dont 6 dynamiques.'),
    supCardsHtml.includes(
      '2 appels à l&#39;API eedomus lors du dernier cycle.'
    ),
    supCardsHtml.includes('Box Salon'),
    supCardsHtml.includes('Sur les 2 derniers cycles de refresh.'),
  ],
  [true, true, true, true, true, true, true]
);
// The coherence link renders and delegates through _setTab — the
// internal-link precedent of the "create a rule" shortcut.
assertEq(
  'supervision: the coherence link renders',
  supCardsHtml.includes('Voir le tableau de cohérence'),
  true
);
const supSetTabCalls = [];
supPanel._setTab = (tab) => {
  supSetTabCalls.push(tab);
};
supPanel._onClick({
  target: {
    closest: (sel) => (sel === '[data-goto-coherence]' ? {} : null),
  },
});
assertEq(
  'supervision: the coherence link calls _setTab(coherence)',
  supSetTabCalls,
  ['coherence']
);
// A box without cycles renders the positive empty state, nominative.
supPanel._metrics = { boxes: [{ entry_id: 'E1', name: 'Salon', cycles: [] }] };
const supEmptyHtml = supPanel._renderSupervisionTab();
assertEq(
  'supervision: zero cycles render the positive empty state',
  [
    supEmptyHtml.includes('Aucun cycle de refresh enregistré'),
    supEmptyHtml.includes('Box Salon'),
  ],
  [true, true]
);
// A box with neither name nor entry_id never renders an empty "Box ".
supPanel._metrics = { boxes: [{ cycles: [] }] };
assertEq(
  'supervision: an anonymous box renders Box #1, never an empty title',
  supPanel._renderSupervisionTab().includes('Box #1'),
  true
);
// Multi-box payload: one section per box, each with its own name.
supPanel._metrics = {
  boxes: [
    {
      entry_id: 'E1',
      name: 'Salon',
      cycles: [
        {
          ts: '2026-10-03T09:05:00',
          refresh_time: 2.1,
          api_time: 1.1,
          api_calls: 2,
          periphs_total: 165,
          periphs_dynamic: 6,
        },
      ],
    },
    { entry_id: 'E2', name: 'Cave', cycles: [] },
  ],
};
const supMultiHtml = supPanel._renderSupervisionTab();
assertEq(
  'supervision: a multi-box payload renders one named section per box',
  [
    (supMultiHtml.match(/supervision-section/g) || []).length,
    supMultiHtml.includes('Box Salon'),
    supMultiHtml.includes('Box Cave'),
  ],
  [2, true, true]
);
// Deep link: the #supervision hash activates the tab from location,
// an unknown hash falls back (the hash is the source of truth).
sandbox.window.location.hash = '#supervision';
assertEq(
  'supervision: deep link #supervision resolves to the tab',
  new EedomusConfigPanel()._tabFromLocation(),
  'supervision'
);
sandbox.window.location.hash = '';
assertEq(
  'supervision: an absent hash falls back to peripheriques',
  new EedomusConfigPanel()._tabFromLocation(),
  'peripheriques'
);
// The Retry delegation clears the error and re-issues the load.
supPanel._metricsError = 'panel.common.command_refused';
const supReloads = [];
supPanel._loadMetrics = () => {
  supReloads.push(1);
};
supPanel._onClick({
  target: {
    closest: (sel) =>
      sel === '.retry' ? { dataset: { retry: 'metrics' } } : null,
  },
});
assertEq(
  'supervision: the Retry button clears the error and re-issues the load',
  [supReloads.length, supPanel._metricsError],
  [1, null]
);

// Sync suite boundary: a sync failure exits before the async block.
if (failures) {
  console.log(`\n${failures} failure(s)`);
  process.exit(1);
}

// ====================================================================
// CAP-3 (ticket 3.3) — catalog consumption, below the sync suite: the
// lifecycle tests drive set hass with a stubbed callWS and a stubbed
// shadow root; the search test drives the Peripherals-tab empty state.
// ====================================================================

// One macrotask: the async _loadStrings continuations settle before
// the assertions run (the panel's own setTimeout stays sandboxed).
const tick = () => new Promise((resolve) => setTimeout(resolve, 0));

// Fresh panel over a recording shadow-root stub: the delegation
// handlers land in listeners[type] so the once-only attachment is
// observable.
function lifecyclePanel() {
  const panel = new EedomusConfigPanel();
  panel.shadowRoot = {
    innerHTML: '',
    listeners: {},
    addEventListener(type, handler) {
      (this.listeners[type] = this.listeners[type] || []).push(handler);
    },
    removeEventListener() {},
    getElementById: () => null,
    querySelector: () => null,
    querySelectorAll: () => [],
  };
  return panel;
}

async function runCatalogLifecycleTests() {
  // (1) the command is issued with hass.locale.language
  const issued = [];
  const firstPanel = lifecyclePanel();
  firstPanel.hass = {
    locale: { language: 'fr' },
    callWS: async (msg) => {
      issued.push(msg);
      return { locale: 'fr', translations: FR };
    },
  };
  await tick();
  assertEq(
    'lifecycle: get_translations issued with the hass locale',
    issued,
    [{ type: 'eedomus/get_translations', locale: 'fr' }]
  );
  assertEq(
    'lifecycle: catalog stored with its locale',
    [firstPanel._stringsLocale, firstPanel.t('panel.common.retry')],
    ['fr', 'Réessayer']
  );

  // (2) a rejected callWS leaves _strings null; a second set hass
  // re-issues the command (silent retry, skeleton in between).
  const failPanel = lifecyclePanel();
  let failCalls = 0;
  const refuse = () => {
    failCalls += 1;
    return Promise.reject(new Error('commande refusée'));
  };
  failPanel.hass = { locale: { language: 'fr' }, callWS: refuse };
  await tick();
  assertEq(
    'lifecycle: ws failure leaves no catalog, no throw',
    [failPanel._strings, failPanel.t('panel.common.retry')],
    [null, 'panel.common.retry']
  );
  failPanel.hass = { locale: { language: 'fr' }, callWS: refuse };
  await tick();
  assertEq(
    'lifecycle: second set hass re-issues the command',
    failCalls,
    2
  );

  // (3) a locale change requests the new locale and swaps the catalog
  const locales = [];
  const localePanel = lifecyclePanel();
  localePanel.hass = {
    locale: { language: 'fr' },
    callWS: async (msg) => {
      locales.push(msg.locale);
      return { locale: 'fr', translations: FR };
    },
  };
  await tick();
  localePanel.hass = {
    locale: { language: 'en' },
    callWS: async (msg) => {
      locales.push(msg.locale);
      return { locale: 'en', translations: { 'panel.common.title': 'X' } };
    },
  };
  await tick();
  assertEq(
    'lifecycle: locale change requests the new locale, catalog swaps',
    [locales, localePanel._stringsLocale, localePanel._strings['panel.common.title']],
    [['fr', 'en'], 'en', 'X']
  );

  // (4) a locale change mid-flight discards the stale response
  const stalePanel = lifecyclePanel();
  let resolveFr;
  const frInFlight = new Promise((resolve) => {
    resolveFr = resolve;
  });
  stalePanel.hass = { locale: { language: 'fr' }, callWS: () => frInFlight };
  // The locale flips before the fr response arrives.
  stalePanel.hass = {
    locale: { language: 'en' },
    callWS: async () => ({
      locale: 'en',
      translations: { 'panel.common.title': 'EN' },
    }),
  };
  await tick();
  resolveFr({ locale: 'fr', translations: FR });
  await tick();
  assertEq(
    'lifecycle: stale in-flight response is discarded',
    [stalePanel._stringsLocale, stalePanel._strings['panel.common.title']],
    ['en', 'EN']
  );

  // (5) + (6) + (7) one panel: gate, catalog arrival, delegation
  const gatePanel = lifecyclePanel();
  gatePanel._render();
  const gatedHtml = gatePanel.shadowRoot.innerHTML;
  assertEq(
    'lifecycle: catalog-absent render is skeleton only, no key text',
    [
      gatedHtml.includes('skeleton-row'),
      gatedHtml.includes('role="status"'),
      gatedHtml.includes('aria-busy="true"'),
      !gatedHtml.includes('panel.'),
      !gatedHtml.includes('tab-content'),
    ],
    [true, true, true, true, true]
  );
  gatePanel.hass = {
    locale: { language: 'fr' },
    callWS: async () => ({ locale: 'fr', translations: FR }),
  };
  await tick();
  const liveHtml = gatePanel.shadowRoot.innerHTML;
  assertEq(
    'lifecycle: catalog arrival re-renders real content',
    [
      liveHtml.includes('Périphériques'),
      liveHtml.includes('id="tab-content"'),
      gatePanel._stringsLocale,
    ],
    [true, true, 'fr']
  );
  assertEq(
    'lifecycle: composed styles carry every tab chunk',
    [
      liveHtml.includes('.periph-list {'),
      liveHtml.includes('.rule-form {'),
      liveHtml.includes('.version-card {'),
      liveHtml.includes('.coherence-table-wrap {'),
    ],
    [true, true, true, true]
  );
  assertEq(
    'lifecycle: delegation listeners attached exactly once',
    gatePanel.shadowRoot.listeners.click.length,
    1
  );
  let onClickRuns = 0;
  const realOnClick = gatePanel._onClick;
  gatePanel._onClick = (ev) => {
    onClickRuns += 1;
    return realOnClick.call(gatePanel, ev);
  };
  gatePanel.shadowRoot.listeners.click[0]({
    target: { closest: () => null },
    preventDefault: () => {},
    stopPropagation: () => {},
  });
  assertEq(
    'lifecycle: one dispatched click runs the delegation once',
    onClickRuns,
    1
  );

  // (8) direct lazy entry on every tab: the tab rendered before hass
  // was assigned, its lazy load bailed out — set hass restarts it
  // (closes #regles and bug 105 #historique alongside #coherence).
  const lazyAnswers = {
    'eedomus/get_translations': { locale: 'fr', translations: FR },
    'eedomus/get_peripherals': { peripherals: [] },
    'eedomus/get_mapping': { mapping: {} },
    'eedomus/get_mapping_versions': { versions: [], current: {} },
    'eedomus/get_coherence': { peripherals: [] },
    'eedomus/get_box_metrics': { boxes: [] },
  };
  const lazyIssued = [];
  const lazyHass = {
    locale: { language: 'fr' },
    callWS: async (msg) => {
      lazyIssued.push(`${msg.type}`);
      return lazyAnswers[msg.type] || {};
    },
  };
  for (const [lazyTab, lazyCommand] of [
    ['regles', 'eedomus/get_mapping'],
    ['historique', 'eedomus/get_mapping_versions'],
    ['coherence', 'eedomus/get_coherence'],
    ['supervision', 'eedomus/get_box_metrics'],
  ]) {
    const panel = lifecyclePanel();
    panel._tab = lazyTab;
    panel._render();
    panel.hass = lazyHass;
    await tick();
    assertEq(
      `lifecycle: direct #${lazyTab} entry starts its lazy load once hass arrives`,
      [
        lazyIssued.includes(lazyCommand),
        lazyIssued.filter((cmd) => cmd === lazyCommand).length,
      ],
      [true, 1]
    );
    lazyIssued.length = 0;
  }

  // (9) the Retry button of the coherence error state re-issues the
  // load after clearing the error (never a stale error table).
  const retryPanel = lifecyclePanel();
  retryPanel._built = true;
  retryPanel._tab = 'coherence';
  retryPanel._coherenceError = 'panel.common.command_refused';
  const retryLoads = [];
  retryPanel._loadCoherence = () => {
    retryLoads.push(1);
  };
  retryPanel._onClick({
    target: {
      closest: (sel) =>
        sel === '.retry' ? { dataset: { retry: 'coherence' } } : null,
    },
  });
  assertEq(
    'lifecycle: the Retry button clears the error and re-issues the load',
    [retryLoads.length, retryPanel._coherenceError],
    [1, null]
  );

  // (10) a mapping write invalidates the coherence cache: the next
  // visit to the tab reloads the signals instead of showing the
  // pre-write rows until a full panel reload.
  const writePanel = lifecyclePanel();
  writePanel._strings = FR;
  writePanel._stringsLocale = 'fr';
  writePanel._coherence = [{ periph_id: '101', signals: ['regle_active'] }];
  writePanel._coherenceError = null;
  writePanel._mapping = { custom_usage_id_mappings: {} };
  writePanel._hass = {
    locale: { language: 'fr' },
    callWS: async () => ({ peripherals: [] }),
  };
  const writeOk = await writePanel._persistMapping({
    custom_usage_id_mappings: {},
  });
  assertEq(
    'lifecycle: a successful mapping write invalidates the coherence cache',
    [writeOk, writePanel._coherence, writePanel._coherenceError],
    [true, null, null]
  );
  const reloadCalls = [];
  writePanel._loadCoherence = () => {
    reloadCalls.push(1);
  };
  // _renderTabContent renders into #tab-content before starting the
  // lazy load - the stub must hand it a content element.
  writePanel.shadowRoot = {
    addEventListener() {},
    removeEventListener() {},
    getElementById: (id) =>
      id === 'tab-content' ? { innerHTML: '' } : null,
    querySelector: () => null,
    querySelectorAll: () => [],
  };
  writePanel._tab = 'coherence';
  writePanel._renderTabContent();
  assertEq(
    'lifecycle: returning to the coherence tab reloads the signals',
    reloadCalls.length,
    1
  );

  // (11) a get_translations call that never settles (dropped ws): the
  // timeout race frees the loading slot, the next set hass re-issues.
  const timeoutPanel = lifecyclePanel();
  let timeoutCalls = 0;
  const droppedHass = () => ({
    locale: { language: 'fr' },
    callWS: (msg) => {
      if (msg.type === 'eedomus/get_translations') {
        timeoutCalls += 1;
        return new Promise(() => {}); // never settles
      }
      return Promise.resolve({ peripherals: [] });
    },
  });
  timeoutPanel.hass = droppedHass();
  await tick();
  assertEq(
    'lifecycle: a dropped get_translations keeps the slot busy mid-flight',
    [timeoutPanel._stringsLoadingLocale, timeoutCalls],
    ['fr', 1]
  );
  // The STRINGS_LOAD_TIMEOUT_MS timer is the last one scheduled.
  const stringsTimer = sandboxTimers[sandboxTimers.length - 1];
  assertEq(
    'lifecycle: the timeout race is armed at STRINGS_LOAD_TIMEOUT_MS',
    stringsTimer.delay,
    10000
  );
  stringsTimer.fn();
  await tick();
  assertEq(
    'lifecycle: the timeout wins the race and frees the loading slot',
    [timeoutPanel._stringsLoadingLocale, timeoutPanel._strings],
    [null, null]
  );
  timeoutPanel.hass = droppedHass();
  await tick();
  assertEq(
    'lifecycle: the next set hass re-issues the dropped command',
    timeoutCalls,
    2
  );

  // (12) a successful rule delete invalidates the coherence cache too
  // (the delete path has its own save_mapping call, outside
  // _persistMapping).
  const deletePanel = lifecyclePanel();
  deletePanel._strings = FR;
  deletePanel._stringsLocale = 'fr';
  deletePanel._tab = 'regles';
  deletePanel._mapping = {
    custom_usage_id_mappings: { '7': { ha_entity: 'sensor' } },
  };
  deletePanel._coherence = [{ periph_id: '101', signals: ['regle_active'] }];
  const deleteCalls = [];
  deletePanel._hass = {
    locale: { language: 'fr' },
    callWS: async (msg) => {
      deleteCalls.push(msg.type);
      return { peripherals: [] };
    },
  };
  // Two-gesture delete: the first call arms the confirmation only.
  await deletePanel._deleteRule('7');
  await deletePanel._deleteRule('7');
  assertEq(
    'lifecycle: a successful rule delete invalidates the coherence cache',
    [deleteCalls.includes('eedomus/save_mapping'), deletePanel._coherence],
    [true, null]
  );

  // (13) a coherence load still in flight when a write invalidates
  // the cache must not repopulate it: the generation guard discards
  // the stale resolution, the next visit reloads.
  const staleCachePanel = lifecyclePanel();
  staleCachePanel._strings = FR;
  staleCachePanel._stringsLocale = 'fr';
  staleCachePanel._coherence = [{ periph_id: '101', signals: ['regle_active'] }];
  let resolveCoherence;
  const coherenceInFlight = new Promise((resolve) => {
    resolveCoherence = resolve;
  });
  staleCachePanel._hass = {
    locale: { language: 'fr' },
    callWS: (msg) =>
      msg.type === 'eedomus/get_coherence'
        ? coherenceInFlight
        : Promise.resolve({ peripherals: [] }),
  };
  staleCachePanel._loadCoherence();
  // A mapping write lands while the coherence request is in flight.
  staleCachePanel._invalidateCoherenceCache();
  resolveCoherence({
    peripherals: [{ periph_id: '101', signals: ['regle_active'] }],
  });
  await tick();
  assertEq(
    'lifecycle: an in-flight load resolved after the invalidation is discarded',
    [staleCachePanel._coherence, staleCachePanel._coherenceLoading],
    [null, false]
  );

  // (14) the post-timeout duplicate-call race: call 1 drops, the
  // locale flips (call 2 loads), flips BACK (call 3 in flight, same
  // locale VALUE as call 1) — firing call 1's still-armed timeout is
  // then a late continuation. Value-identical locales must not let
  // it erase call 3's loading marker: the next set hass stays
  // deduplicated, and call 3's own timeout is what frees the slot.
  const racePanel = lifecyclePanel();
  let raceFrCalls = 0;
  const raceHass = (lang) => ({
    locale: { language: lang },
    callWS: (msg) => {
      if (msg.type !== 'eedomus/get_translations') {
        return Promise.resolve({ peripherals: [] });
      }
      if (msg.locale === 'fr') {
        raceFrCalls += 1;
        return new Promise(() => {}); // dropped: never settles
      }
      return Promise.resolve({
        locale: 'en',
        translations: { 'panel.common.title': 'EN' },
      });
    },
  });
  // Timer identity, not delay or array position: the strings timeout is
  // the last timer scheduled by each set hass (armed synchronously
  // inside _loadStrings), so each call's handle is captured right at
  // stub time — a STRINGS_LOAD_TIMEOUT_MS change cannot degrade the
  // race assertions below.
  racePanel.hass = raceHass('fr'); // call 1: dropped, timeout armed
  const call1Timer = sandboxTimers[sandboxTimers.length - 1];
  await tick();
  racePanel.hass = raceHass('en'); // call 2: resolves, EN catalog stored
  const call2Timer = sandboxTimers[sandboxTimers.length - 1];
  await tick();
  racePanel.hass = raceHass('fr'); // call 3: dropped, in flight
  const call3Timer = sandboxTimers[sandboxTimers.length - 1];
  await tick();
  assertEq(
    'lifecycle: race setup armed three distinct strings timeouts',
    [call1Timer, call2Timer, call3Timer].every(
      (timer, idx, all) => all.indexOf(timer) === idx
    ),
    true
  );
  // Call 1's timeout fires long after call 3 took over the locale.
  call1Timer.fn();
  await tick();
  assertEq(
    'lifecycle: a late continuation does not erase the in-flight marker',
    [racePanel._stringsLoadingLocale, raceFrCalls],
    ['fr', 2]
  );
  // The marker surviving means the next set hass stays deduplicated.
  racePanel.hass = raceHass('fr');
  await tick();
  assertEq(
    'lifecycle: no duplicate get_translations while the retry is in flight',
    raceFrCalls,
    2
  );
  // Call 3's own timeout frees the slot, and only then does a new
  // set hass re-issue the dropped command.
  call3Timer.fn();
  await tick();
  assertEq(
    'lifecycle: the in-flight call keeps ownership of the slot until its own timeout',
    racePanel._stringsLoadingLocale,
    null
  );
  racePanel.hass = raceHass('fr');
  await tick();
  assertEq(
    'lifecycle: after the in-flight call times out the next set hass re-issues',
    raceFrCalls,
    3
  );

  // (15) the generation guard's SUCCESS path: a superseded call that
  // RESOLVES successfully (no timeout involved) after a newer call
  // started writes no catalog and leaves the newer call's loading
  // marker alone — only the timeout path was covered above.
  const supersedePanel = lifecyclePanel();
  let resolveSupersededCatalog;
  const supersedeHass = (lang) => ({
    locale: { language: lang },
    callWS: (msg) => {
      if (msg.type !== 'eedomus/get_translations') {
        return Promise.resolve({ peripherals: [] });
      }
      if (msg.locale === 'fr') {
        // Call 1: succeeds, but only after the newer call took over.
        return new Promise((resolve) => {
          resolveSupersededCatalog = resolve;
        });
      }
      // Call 2 (en): stays in flight, owning the loading slot.
      return new Promise(() => {});
    },
  });
  supersedePanel.hass = supersedeHass('fr'); // call 1
  await tick();
  supersedePanel.hass = supersedeHass('en'); // call 2: supersedes call 1
  await tick();
  // Call 1's late success would write the FR catalog and clear the
  // marker: the generation guard must discard both.
  resolveSupersededCatalog({
    locale: 'fr',
    translations: { 'panel.common.title': 'FR' },
  });
  await tick();
  assertEq(
    'lifecycle: a superseded success writes no catalog and keeps the newer marker',
    [supersedePanel._strings, supersedePanel._stringsLoadingLocale],
    [null, 'en']
  );
}

// --- Supervision async lifecycle (4.2 review patches) --------------
// Generation supersession of _loadMetrics, and the raw-error-detail
// render path (escaped, untranslated) — both driven with stubbed
// callWS answers, same model as the catalog lifecycle tests.
async function runSupervisionAsyncTests() {
  // A pending get_box_metrics superseded by a newer load writes
  // nothing stale: the generation guard discards the resolution.
  const metricsPanel = lifecyclePanel();
  let resolveMetrics;
  const pendingMetrics = new Promise((resolve) => {
    resolveMetrics = resolve;
  });
  metricsPanel._hass = {
    locale: { language: 'fr' },
    callWS: (msg) =>
      msg.type === 'eedomus/get_box_metrics'
        ? pendingMetrics
        : Promise.resolve({ locale: 'fr', translations: FR }),
  };
  const metricsLoad = metricsPanel._loadMetrics();
  // A newer load supersedes while the request is in flight.
  metricsPanel._metricsGeneration += 1;
  resolveMetrics({ boxes: [{ entry_id: 'E1', cycles: [] }] });
  await metricsLoad;
  await tick();
  assertEq(
    'supervision: a superseded in-flight load writes nothing stale',
    [metricsPanel._metrics, metricsPanel._metricsLoading],
    [null, false]
  );

  // The raw backend error detail renders escaped and as-is - never a
  // second pass through t() (FR users would read untranslated text,
  // and {token}-shaped details would go through token replacement).
  const rawPanel = lifecyclePanel();
  rawPanel._strings = FR;
  rawPanel._stringsLocale = 'fr';
  rawPanel._tab = 'supervision';
  rawPanel._hass = {
    locale: { language: 'fr' },
    callWS: (msg) =>
      msg.type === 'eedomus/get_box_metrics'
        ? Promise.reject(new Error('Service unreachable <script>'))
        : Promise.resolve({ locale: 'fr', translations: FR }),
  };
  await rawPanel._loadMetrics();
  const rawHtml = rawPanel._renderSupervisionTab();
  assertEq(
    'supervision: a raw error detail renders escaped, untranslated',
    [
      rawHtml.includes('Impossible de charger les métriques : '),
      rawHtml.includes('Service unreachable &lt;script&gt;'),
      rawHtml.includes('<script>'),
    ],
    [true, true, false]
  );
}

// --- periphs search-no-result state (CAP-3 spine row, 3.3) ---
function runPeriphSearchTests() {
  const searchPanel = new EedomusConfigPanel();
  searchPanel._strings = FR;
  searchPanel._stringsLocale = 'fr';
  const periphEls = {
    'periph-list': { id: 'periph-list', innerHTML: '' },
    'periph-status': { id: 'periph-status', textContent: '' },
    'periph-status-live': { id: 'periph-status-live', textContent: '' },
  };
  searchPanel.shadowRoot = {
    querySelector: () => null,
    getElementById: (id) => periphEls[id] || null,
  };
  searchPanel._tab = 'peripheriques';
  searchPanel._periphs = [
    { periph_id: '101', name: 'Salon', usage_id: '1', entity_id: 'sensor.s' },
    { periph_id: '12', name: 'Cave', usage_id: '2', entity_id: null },
  ];
  searchPanel._search = 'zzz';
  searchPanel._renderPeriphList();
  assertEq(
    'periphs search: empty-search state message renders',
    periphEls['periph-list'].innerHTML.includes(
      'Aucun périphérique ne correspond à “zzz”'
    ),
    true
  );
  assertEq(
    'periphs search: count status keeps announcing',
    [
      periphEls['periph-status'].textContent,
      periphEls['periph-status-live'].textContent,
    ],
    ['2 périphériques', '2 périphériques']
  );
}

runPeriphSearchTests();

// --- payload JSON copy (UX run 3): stubbed clipboard, both verdicts ---
// The handler resolves navigator/document at call time, so the vm
// sandbox globals below are observable to the panel scope. The
// navigator/document stubs are restored in the finally block — a
// later chained test sees clean globals.
async function runCopyJsonTests() {
  const RAW_TEXT = JSON.stringify(ORDERED_RAW, null, 2);
  const codeEl = { textContent: RAW_TEXT };
  // The lookup selector is derived from what coherenceDetailHtml
  // actually emits (pre class + inner tag), not from the handler's
  // own literal — a markup/handler drift makes the stub answer null
  // and the success paths fail loudly.
  const emittedRaw = coherenceDetailHtml(
    { periph_id: '101', name: 'Salon', raw: ORDERED_RAW },
    t
  ).match(/<details class="popover-raw">([\s\S]*?)<\/details>/)[1];
  const emittedPre = emittedRaw.match(/<pre class="([^"]+)"><(\w+)>/);
  if (!emittedPre) {
    throw new Error('coherenceDetailHtml emits no raw JSON pre/code block');
  }
  const markupSelector = `.${emittedPre[1]} ${emittedPre[2]}`;
  const detailsStub = {
    querySelector: (sel) => (sel === markupSelector ? codeEl : null),
  };
  const buttonStub = {
    closest: (sel) => (sel === 'details' ? detailsStub : null),
  };
  const copyPanel = new EedomusConfigPanel();
  copyPanel._strings = FR;
  const copyLive = { id: 'copy-status-live', textContent: '' };
  copyPanel.shadowRoot = {
    getElementById: (id) => (id === 'copy-status-live' ? copyLive : null),
  };

  const savedNavigator = sandbox.navigator;
  const savedDocument = sandbox.document;
  const restoreSandbox = () => {
    if (savedNavigator === undefined) {
      delete sandbox.navigator;
    } else {
      sandbox.navigator = savedNavigator;
    }
    if (savedDocument === undefined) {
      delete sandbox.document;
    } else {
      sandbox.document = savedDocument;
    }
  };

  try {
    // Delegation: the [data-copy-json] branch of _onClick routes the
    // button to the handler (spy — removing the branch ships a dead
    // button with the suite green).
    const routed = [];
    copyPanel._copyCoherenceRawJson = (btn) => {
      routed.push(btn);
      return Promise.resolve();
    };
    copyPanel._onClick({
      target: {
        closest: (sel) => (sel === '[data-copy-json]' ? buttonStub : null),
      },
    });
    assertEq(
      'copy delegation: _onClick routes the copy button to the handler',
      [routed.length, routed[0] === buttonStub],
      [1, true]
    );
    copyPanel._copyCoherenceRawJson =
      EedomusConfigPanel.prototype._copyCoherenceRawJson;

    // Success: the clipboard receives the exact rendered JSON and the
    // verdict is announced in the dedicated live region.
    const written = [];
    sandbox.navigator = {
      clipboard: {
        writeText: (text) => {
          written.push(text);
          return Promise.resolve();
        },
      },
    };
    await copyPanel._copyCoherenceRawJson(buttonStub);
    assertEq(
      'copy: clipboard success writes the JSON and announces it',
      [written, copyLive.textContent],
      [[RAW_TEXT], 'JSON copié.']
    );

    // Missing source read: no code element (selector drift) or empty
    // text — the announced verdict is the failure, nothing is written.
    const emptyDetailsStub = {
      querySelector: () => ({ textContent: '' }),
    };
    const emptyButtonStub = {
      closest: (sel) => (sel === 'details' ? emptyDetailsStub : null),
    };
    await copyPanel._copyCoherenceRawJson(emptyButtonStub);
    const noCodeButtonStub = {
      closest: (sel) => (sel === 'details' ? { querySelector: () => null } : null),
    };
    await copyPanel._copyCoherenceRawJson(noCodeButtonStub);
    assertEq(
      'copy: missing or empty source announces the failure, copies nothing',
      [written, copyLive.textContent],
      [[RAW_TEXT], 'Copie impossible.']
    );

    // Refusal: the API rejects and no execCommand fallback exists (no
    // document in the sandbox yet) — the failure is announced, never
    // silent.
    sandbox.navigator = {
      clipboard: {
        writeText: () => Promise.reject(new Error('denied')),
      },
    };
    await copyPanel._copyCoherenceRawJson(buttonStub);
    assertEq(
      'copy: refused clipboard announces « Copie impossible. »',
      copyLive.textContent,
      'Copie impossible.'
    );

    // Fallback: no clipboard API at all, execCommand succeeds. The
    // created textarea is captured — the copied text is asserted, an
    // empty-string fallback would stay green otherwise.
    const execLog = [];
    const areaLog = [];
    let createdArea = null;
    sandbox.navigator = {};
    sandbox.document = {
      createElement: () => {
        createdArea = {
          value: '',
          style: {},
          setAttribute() {},
          focus() {
            areaLog.push('focus');
          },
          select() {
            areaLog.push('select');
          },
        };
        return createdArea;
      },
      execCommand: (cmd) => {
        execLog.push(cmd);
        return true;
      },
      body: {
        appendChild() {
          areaLog.push('append');
        },
        removeChild() {
          areaLog.push('remove');
        },
      },
    };
    await copyPanel._copyCoherenceRawJson(buttonStub);
    assertEq(
      'copy: execCommand fallback copies the text, focuses, and announces',
      [execLog, areaLog, createdArea.value, copyLive.textContent],
      [['copy'], ['append', 'focus', 'select', 'remove'], RAW_TEXT, 'JSON copié.']
    );

    // Fallback refusal: execCommand answers false — the failure is
    // announced on the copy-status-live region too.
    sandbox.document.execCommand = () => false;
    await copyPanel._copyCoherenceRawJson(buttonStub);
    assertEq(
      'copy: execCommand refusal announces the failure too',
      copyLive.textContent,
      'Copie impossible.'
    );
  } finally {
    restoreSandbox();
  }
}

runCatalogLifecycleTests()
  .then(runSupervisionAsyncTests)
  .then(runCopyJsonTests)
  .then(
  () => {
    if (failures) {
      console.log(`\n${failures} failure(s)`);
      process.exit(1);
    }
    console.log('\nAll coherence tests passed.');
  },
  (err) => {
    console.error(err);
    process.exit(1);
  }
);
