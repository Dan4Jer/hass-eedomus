'use strict';

/**
 * Node-run tests for the coherence pure helpers (ticket 2.3).
 *
 * The panel is a plain browser script with no build toolchain, so this
 * loads it in a vm with stubbed browser globals and asserts on the
 * top-level pure functions exported by the module scope.
 *
 * Since CAP-3 the label-bearing helpers take a translator as their
 * last argument; the tests pass a fixture built from the frozen FR
 * catalog (tests/js/fr-catalog.js parses panel_translations.py), so
 * the expected texts below stay the real FR panel texts.
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
  periphStatusText,
  coherenceStatusText,
  COHERENCE_COLUMNS,
};`;
vm.runInContext(fs.readFileSync(PANEL_PATH, 'utf8') + hook, sandbox);
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
  periphStatusText,
  coherenceStatusText,
  COHERENCE_COLUMNS,
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

// --- popover: état vivant fields (ticket 2.4) ---
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
  'live: row without entity shows « aucune entité » and no value',
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
    // CAP-8 : l'action « Config HA » désactivée est devenue le lien
    // actif « Voir dans HA » — le libellé accessible porte l'entité.
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
  'detail: non-numeric attempts never pluralize as NaN',
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
    // Sans entité, aucun lien ni action de navigation (CAP-8).
    !noEntityDetail.includes('data-entity-id'),
    !noEntityDetail.includes('Voir dans HA'),
  ],
  [true, true, true, true, true, true]
);

// --- entity link (2.6, CAP-8): markup, hostile and null cases ---
assertEq(
  'entity link: null/undefined/empty stays inert « aucune entité »',
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
  [1, 300, '1 périphériques', []]
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
  [['1 périphériques'], undefined]
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
  [undefined, 3, 3, '1 périphériques']
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

// Sync suite boundary: a sync failure exits before the async block.
if (failures) {
  console.log(`\n${failures} failure(s)`);
  process.exit(1);
}

// ====================================================================
// CAP-3 (ticket 3.3) — catalog consumption, below the sync suite: the
// lifecycle tests drive set hass with a stubbed callWS and a stubbed
// shadow root; the search test drives the Périphériques empty state.
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

runCatalogLifecycleTests().then(
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
