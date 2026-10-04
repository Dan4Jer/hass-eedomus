/**
 * Eedomus Config panel — webcomponent served at /local/eedomus/eedomus-panel.js
 *
 * P.1.3 implements the Périphériques tab (mock-01): list of peripherals from
 * coordinator.data via the eedomus/get_peripherals websocket command, search
 * by name or usage_id, "Périphériques touchés" filter, accessible modified
 * badge, and the "Créer une règle" shortcut that pre-fills the usage_id for
 * the Règles tab. Règles and Historique are placeholders until P.1.4-P.1.6.
 *
 * Theming: HA CSS variables only (no hard-coded style). The panel is
 * keyboard-operable and announces state changes through aria-live.
 */

const TABS = ['peripheriques', 'regles', 'historique', 'coherence'];
const TAB_LABELS = {
  peripheriques: 'Périphériques',
  regles: 'Règles',
  historique: 'Historique',
};

// Coherence signals (CAP-6): exact strings from eedomus/get_coherence,
// one chip per signal — glyph + label, never color alone (DESIGN.md).
const COHERENCE_SIGNALS = {
  sans_entite: {
    label: 'sans entité HA',
    icon: '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M12 2C6.47 2 2 6.47 2 12s4.47 10 10 10 10-4.47 10-10S17.53 2 12 2zm5 13.59L15.59 17 12 13.41 8.41 17 7 15.59 10.59 12 7 8.41 8.41 7 12 10.59 15.59 7 17 8.41 13.41 12 17 15.59z"/></svg>',
  },
  douteux: {
    label: 'mapping douteux',
    icon: '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>',
  },
  regle_active: {
    label: 'règle active',
    icon: '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M3 17v2h6v-2H3zM3 5v2h10V5H3zm10 16v-2h8v-2h-8v-2h-2v6h2zM7 9v2H3v2h4v2h2V9H7zm14 4v-2H11v2h10zm-4-4h2V7h4V5h-4V3h-2v6z"/></svg>',
  },
  en_erreur: {
    label: 'en erreur',
    icon: '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M12 6v3l4-4-4-4v3c-4.42 0-8 3.58-8 8 0 1.57.46 3.03 1.24 4.26L6.7 14.8c-.45-.83-.7-1.79-.7-2.8 0-3.31 2.69-6 6-6zm6.76 1.74L17.3 9.2c.44.84.7 1.8.7 2.8 0 3.31-2.69 6-6 6v-3l-4 4 4 4v-3c4.42 0 8-3.58 8-8 0-1.57-.46-3.03-1.24-4.26z"/></svg>',
  },
};
const COHERENCE_OK_SIGNAL = {
  label: 'cohérent',
  icon: '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>',
};
// Shared by the coherence table head generator and its skeleton (sweep)
// so the columns cannot drift: key is the sort key, label the column name.
const COHERENCE_COLUMNS = [
  { key: 'periph_id', label: 'periph_id' },
  { key: 'name', label: 'Nom' },
  { key: 'entity_id', label: 'Entité HA' },
  { key: 'type', label: 'Type / sous-type' },
  { key: 'status', label: 'Statut' },
];
// The single breakpoint of the coherence tab (ticket 2.5): the JS
// surface switch (coherenceNarrowView, matchMedia) and the CSS
// reflow (@media in _render — cross-referenced there) both derive
// from it — one breakpoint, two surfaces.
const COHERENCE_NARROW_PX = 900;
// Debounce of the result-count announcement (sweep): a burst of typing
// in either search field produces ONE screen-reader announcement, once
// typing pauses for this delay. The visible filtering stays real-time.
const SEARCH_ANNOUNCE_DELAY_MS = 300;
// Sort direction indicator: the arrow carries the direction visually,
// aria-sort on the header cell carries the state (EXPERIENCE.md).
const SORT_ARROW_ASC =
  '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M12 5l7 9H5z"/></svg>';
const SORT_ARROW_DESC =
  '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M12 19l-7-9h14z"/></svg>';

// ---- Coherence pure helpers (ticket 2.3) ----
// Top-level and this-free: pure functions over the payload + tab state,
// exercised directly by tests/js/test-coherence.js.

// « À vérifier » predicate: any signal counts, including unknown strings.
function coherenceToVerify(row) {
  return (row.signals || []).length > 0;
}

// Mapping identity first: the coherence table shows what was mapped, the
// effective platform/class is only the fallback.
function coherenceType(row) {
  return [row.ha_entity || row.platform, row.ha_subtype || row.device_class]
    .filter(Boolean)
    .join(' / ');
}

// Statut tie-break severity: en_erreur first, then douteux, then
// sans_entite, then regle_active; unknown signal strings rank last.
const COHERENCE_SIGNAL_SEVERITY = [
  'en_erreur',
  'douteux',
  'sans_entite',
  'regle_active',
];

function coherenceSeverity(signals) {
  let severity = COHERENCE_SIGNAL_SEVERITY.length;
  for (const signal of signals) {
    const rank = COHERENCE_SIGNAL_SEVERITY.indexOf(signal);
    if (rank !== -1 && rank < severity) {
      severity = rank;
    }
  }
  return severity;
}

function coherenceSortValue(row, key) {
  switch (key) {
    case 'periph_id':
      return String(row.periph_id || '');
    case 'name':
      return String(row.name || '');
    case 'entity_id':
      return String(row.entity_id || '');
    case 'type':
      return coherenceType(row);
    default:
      return '';
  }
}

function coherenceCompare(a, b, key) {
  if (key === 'status') {
    // Signal count first, severity as the tie-break for equal counts.
    const av = a.signals || [];
    const bv = b.signals || [];
    if (av.length !== bv.length) {
      return av.length - bv.length;
    }
    if (av.length === 0) {
      return 0;
    }
    return coherenceSeverity(av) - coherenceSeverity(bv);
  }
  return coherenceSortValue(a, key).localeCompare(
    coherenceSortValue(b, key),
    undefined,
    { numeric: true }
  );
}

// Composition: filter first (view + text), then sort the filtered result.
// The sort works on a copy so the neutral state restores response order.
function filterCoherenceRows(rows, state) {
  let out = rows;
  if (state.view === 'to_verify') {
    out = out.filter(coherenceToVerify);
  }
  if (state.search) {
    const q = state.search.toLowerCase();
    out = out.filter(
      (row) =>
        (row.name || '').toLowerCase().includes(q) ||
        String(row.periph_id || '').toLowerCase().includes(q)
    );
  }
  if (state.sort && state.sort.key) {
    const key = state.sort.key;
    const dir = state.sort.dir === 'asc' ? 1 : -1;
    out = out.slice().sort((a, b) => coherenceCompare(a, b, key) * dir);
  }
  return out;
}

// Sort cycle: croissant -> décroissant -> neutre (ordre de réponse).
function nextCoherenceSort(sort, key) {
  if (sort.key !== key) {
    return { key, dir: 'asc' };
  }
  if (sort.dir === 'asc') {
    return { key, dir: 'desc' };
  }
  return { key: null, dir: null };
}

// Shared head generator (sweep): the loaded table and its skeleton
// render the SAME thead markup from COHERENCE_COLUMNS — labels and
// markup, so the columns cannot drift. The skeleton passes the
// neutral sort; the table passes its live sort state.
function coherenceHeadHtml(sort) {
  const cells = COHERENCE_COLUMNS.map((col) => {
    const active = sort.key === col.key;
    const ariaSort = !active
      ? 'none'
      : sort.dir === 'asc' ? 'ascending' : 'descending';
    const stateLabel = !active
      ? ''
      : sort.dir === 'asc'
        ? ', actuellement croissant'
        : ', actuellement décroissant';
    const arrow = !active
      ? ''
      : sort.dir === 'asc'
        ? `<span class="sort-arrow">${SORT_ARROW_ASC}</span>`
        : `<span class="sort-arrow">${SORT_ARROW_DESC}</span>`;
    return `
          <th scope="col" aria-sort="${ariaSort}">
            <button class="sort-header" type="button" data-sort-key="${col.key}"
                    aria-label="Trier par ${col.label}${stateLabel}">
              ${col.label}${arrow}
            </button>
          </th>`;
  });
  return `
      <thead>
        <tr>${cells.join('')}
        </tr>
      </thead>
    `;
}

// Status-line texts (sweep): one pure helper per tab so the immediate
// render path and the debounced announcement compute the exact same
// message — the live region never disagrees with the table.
function periphStatusText(total, shown, touchedOnly) {
  const filterLabel = touchedOnly
    ? ` — filtre « Périphériques touchés » actif : ${shown} résultats`
    : '';
  return `${total} périphériques${filterLabel}`;
}

function coherenceStatusText(shown, search, view) {
  if (shown === 0 && search) {
    return `Aucun périphérique ne correspond à “${search}”.`;
  }
  if (shown === 0 && view === 'to_verify') {
    return 'Tout est cohérent. Aucun périphérique à vérifier.';
  }
  const viewLabel = view === 'to_verify'
    ? ` — vue « À vérifier » active : ${shown} résultats`
    : '';
  return `${shown} périphériques${viewLabel}`;
}

// ---- Popover pure helpers (ticket 2.4) ----
// Same contract as the helpers above: top-level, this-free, exercised
// by tests/js/test-coherence.js. The popover makes no network call —
// everything renders from the already-loaded coherence row.

// Shared value normalizer of the detail fields: null/undefined/empty
// stays null (the renderer shows « inconnu ») — a missing field is
// information, never a silent hole.
function coherenceFieldValue(value) {
  return value == null || value === '' ? null : String(value);
}

// « État vivant » fields. A row without an entity shows
// « aucune entité » and no current value (edge-case matrix).
function coherenceLiveFields(row) {
  const hasEntity = Boolean(row.entity_id);
  return [
    {
      label: 'Entité HA',
      value: hasEntity ? String(row.entity_id) : 'aucune entité',
      mono: true,
    },
    {
      label: 'Valeur courante',
      value: hasEntity ? coherenceFieldValue(row.state) : null,
    },
    { label: 'usage_id', value: coherenceFieldValue(row.usage_id), mono: true },
    {
      label: 'Périphérique parent',
      value: coherenceFieldValue(row.parent_periph_id),
      mono: true,
    },
    {
      label: 'Dernière mise à jour',
      value: coherenceFieldValue(row.last_update),
    },
  ];
}

// Mapping identity fields: what was mapped and why.
function coherenceIdentityFields(row) {
  return [
    { label: 'ha_entity', value: coherenceFieldValue(row.ha_entity), mono: true },
    { label: 'ha_subtype', value: coherenceFieldValue(row.ha_subtype), mono: true },
    { label: 'Justification', value: coherenceFieldValue(row.justification) },
  ];
}

// Raw API section: one pair per top-level key, sorted for scanning;
// nested values render as compact JSON.
function coherenceRawPairs(raw) {
  const entries = Object.entries(raw || {});
  entries.sort((a, b) => a[0].localeCompare(b[0], undefined, { numeric: true }));
  return entries.map(([key, val]) => [
    key,
    val !== null && typeof val === 'object' ? JSON.stringify(val) : String(val),
  ]);
}

// Anchor the popover under the trigger cell, flip above when there is
// strictly more room there, clamp so it never leaves the viewport
// (8 px margin). Pure: the DOM only supplies the rects.
function coherencePopoverPosition(anchor, pop, viewport) {
  const margin = 8;
  const roomBelow = viewport.height - anchor.bottom - margin;
  let top = anchor.bottom + margin;
  if (pop.height > roomBelow && anchor.top - margin > roomBelow) {
    top = anchor.top - margin - pop.height;
  }
  const maxTop = Math.max(margin, viewport.height - pop.height - margin);
  const maxLeft = Math.max(margin, viewport.width - pop.width - margin);
  return {
    left: Math.min(Math.max(anchor.left, margin), maxLeft),
    top: Math.min(Math.max(top, margin), maxTop),
  };
}

// HTML escaping shared by every markup builder below (the _escapeHtml
// method delegates here so the class never diverges).
function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// Trigger of the periph_id cell: the only element of the row that
// opens the detail, carrying its accessible name. The template
// carries aria-expanded only — the popover wiring sets
// aria-haspopup="dialog" dynamically (the narrow surface is an
// inline row, not a dialog), and `controlsId` points at the
// expansion row when it exists (2.5).
function coherenceTriggerHtml(periphId, expanded, controlsId) {
  const controls = controlsId
    ? ` aria-controls="${escapeHtml(controlsId)}"`
    : '';
  return `
    <button class="coherence-id-trigger" type="button"
            data-coherence-popover="${escapeHtml(periphId)}"
            aria-expanded="${expanded ? 'true' : 'false'}"${controls}
            aria-label="Détails du périphérique ${escapeHtml(periphId)}">
      <code>${escapeHtml(periphId)}</code>
    </button>`;
}

// No-entity predicate shared by both surfaces (2.6): a whitespace-only
// entity_id is inert in the table AND the detail — one predicate, the
// two markup helpers cannot drift apart.
function coherenceHasEntity(entityId) {
  return entityId != null && String(entityId).trim() !== '';
}

// Entity cell of the coherence table (ticket 2.6, CAP-8): an inline
// text link — accent, underlined, no button chrome — whose visible
// label is the entity itself. The accessible name carries the action
// and the destination, mirroring the detail's « Voir dans HA ».
// A row without an entity keeps its inert « aucune entité ».
function coherenceEntityLinkHtml(entityId) {
  if (!coherenceHasEntity(entityId)) {
    return '<em>aucune entité</em>';
  }
  return `<a class="entity-link" href="#"
            data-entity-id="${escapeHtml(entityId)}"
            aria-label="Voir ${escapeHtml(entityId)} dans Home Assistant"
           >${escapeHtml(entityId)}</a>`;
}

// Attempts detail of the error state: the plural only applies to a
// finite count > 1 (a non-numeric value never renders NaN).
function coherenceDetailAttempts(attempts) {
  const count = Number(attempts);
  const plural = Number.isFinite(count) && count > 1 ? 's' : '';
  return ` (${escapeHtml(attempts)} tentative${plural})`;
}

// Detail body shared by the desktop popover (2.4) and the mobile
// expanded row (2.5): the same sections from the same coherence row,
// no re-fetch. Everything is eedomus-sourced and escaped.
function coherenceDetailHtml(row) {
  const errorHtml = row.error_message
    ? `<p class="popover-error">
         ${escapeHtml(row.error_message)}
         ${row.retry_after
           ? ` — nouvelle tentative ${escapeHtml(row.retry_after)}`
           : ''}
         ${row.attempts != null ? coherenceDetailAttempts(row.attempts) : ''}
       </p>`
    : '';
  return `
      <div class="popover-head">
        <span class="popover-name">${escapeHtml(row.name || '')}</span>
        <code class="popover-id">${escapeHtml(row.periph_id)}</code>
      </div>
      <div class="popover-section">
        <h3 class="popover-heading">État vivant</h3>
        ${errorHtml}
        <dl>${coherenceDetailFieldsHtml(coherenceLiveFields(row))}</dl>
      </div>
      <div class="popover-section">
        <h3 class="popover-heading">Identité de mapping</h3>
        <dl>${coherenceDetailFieldsHtml(coherenceIdentityFields(row))}</dl>
      </div>
      <div class="popover-actions">
        <button class="row-action" type="button"
                data-periph-id="${escapeHtml(row.periph_id)}"
                data-usage-id="${escapeHtml(row.usage_id || '')}">
          Créer une règle
        </button>
        ${coherenceHasEntity(row.entity_id)
          ? `<button class="row-action" type="button"
                     data-entity-id="${escapeHtml(row.entity_id)}"
                     aria-label="Voir ${escapeHtml(row.entity_id)} dans Home Assistant">
               Voir dans HA
             </button>`
          : ''}
      </div>
      <details class="popover-raw">
        <summary>Champs bruts de l'API eedomus</summary>
        <dl>${coherenceDetailPairsHtml(coherenceRawPairs(row.raw))}</dl>
      </details>
    `;
}

function coherenceDetailFieldsHtml(fields) {
  return fields
    .map((field) => {
      let valueHtml;
      if (field.value == null) {
        valueHtml = '<em class="detail-unknown">inconnu</em>';
      } else if (field.mono) {
        valueHtml = `<span class="detail-code">${escapeHtml(field.value)}</span>`;
      } else {
        valueHtml = `<span>${escapeHtml(field.value)}</span>`;
      }
      return `
          <div class="detail-row">
            <dt>${escapeHtml(field.label)}</dt>
            <dd>${valueHtml}</dd>
          </div>`;
    })
    .join('');
}

function coherenceDetailPairsHtml(pairs) {
  return pairs
    .map(
      ([key, value]) => `
          <div class="detail-row">
            <dt><code class="detail-code">${escapeHtml(key)}</code></dt>
            <dd><code class="detail-code">${escapeHtml(value)}</code></dd>
          </div>`
    )
    .join('');
}

// Focusable elements of the popover: the focus trap cycles through
// these — a disabled control is never a trap stop (uniform [disabled]
// exclusion across every native control, summary included).
const POPOVER_FOCUSABLE_SELECTOR = [
  'button:not([disabled])',
  '[href]',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  'summary',
].join(', ');

// Hover capability: a tap fires mouseover on touch devices — the
// hover-open path must not run there (the click path stays; 2.5
// replaces it with the expanded row).
let hoverMediaQuery = null;
function hoverCapable() {
  if (!window.matchMedia) {
    return false;
  }
  if (!hoverMediaQuery) {
    hoverMediaQuery = window.matchMedia('(hover: hover) and (pointer: fine)');
  }
  return hoverMediaQuery.matches;
}

// Narrow viewport (ticket 2.5): the exact breakpoint of the mobile
// reflow below. matchMedia — not a width read at tap time — keeps
// the tap-vs-popover switch and the CSS reflow on one source of
// truth; a browser without matchMedia reads as desktop (popover).
let narrowMediaQuery = null;
function coherenceNarrowMedia() {
  if (!window.matchMedia) {
    return null;
  }
  if (!narrowMediaQuery) {
    narrowMediaQuery = window.matchMedia(
      `(max-width: ${COHERENCE_NARROW_PX}px)`
    );
  }
  return narrowMediaQuery;
}

function coherenceNarrowView() {
  const media = coherenceNarrowMedia();
  return Boolean(media && media.matches);
}

// Toggle decision of the mobile expanded row (ticket 2.5): re-tap
// on the open line closes, tap on another line moves the extension
// (one line expanded at most), null taps never open. Same contract
// as nextCoherenceSort — pure, test-covered.
function nextCoherenceExpanded(currentId, tappedId) {
  const current = currentId == null ? null : String(currentId);
  const tapped = tappedId == null ? null : String(tappedId);
  if (tapped === null || tapped === current) {
    return null;
  }
  return tapped;
}

// Predicate of the expanded emission: the row identity compares on
// String(periph_id) — the same normalization as the popover lookup,
// so an id with &, quotes or angle brackets expands exactly like the
// popover opens.
function coherenceIsExpanded(row, expandedId, narrow) {
  return Boolean(
    narrow &&
      expandedId != null &&
      String(row.periph_id) === String(expandedId)
  );
}

// DOM id of the expansion row — the trigger's aria-controls target.
function coherenceExpandedRowId(periphId) {
  return `coherence-expanded-${String(periphId)}`;
}

// The expansion row itself: the shared detail body (strict parity
// with the popover) inside the table reflow, spanning every column.
function coherenceExpandedRowHtml(row) {
  return `
      <tr class="coherence-expanded-row"
          id="${escapeHtml(coherenceExpandedRowId(row.periph_id))}">
        <td colspan="${COHERENCE_COLUMNS.length}">
          <div class="coherence-expanded-body">${coherenceDetailHtml(row)}</div>
        </td>
      </tr>
    `;
}

// Composed detail surface of one row: the trigger (aria-expanded
// reflecting the state, aria-controls only when the target exists)
// and the expansion row when the predicate says so — nothing of it
// otherwise (the wide side never emits an expansion).
function coherenceRowExpansionHtml(row, expandedId, narrow) {
  const expanded = coherenceIsExpanded(row, expandedId, narrow);
  return {
    expanded,
    rowClass: expanded ? ' class="coherence-row-expanded"' : '',
    trigger: coherenceTriggerHtml(
      row.periph_id,
      expanded,
      expanded ? coherenceExpandedRowId(row.periph_id) : null
    ),
    expansion: expanded ? coherenceExpandedRowHtml(row) : '',
  };
}

// Truncation of the error detail in the chip (visible + accessible
// name, the full message lives in the title).
function coherenceTruncateText(text, max) {
  const value = String(text);
  if (value.length <= max) {
    return value;
  }
  return `${value.slice(0, max - 1)}…`;
}

// Chips of the Statut cell: one chip per signal, « cohérent » when
// there is none; an unknown string keeps a neutral chip carrying
// the raw value — never dropped, never "cohérent".
function coherenceChipsHtml(row) {
  const signals = (row && row.signals) || [];
  if (signals.length === 0) {
    return coherenceChipHtml('coherent', row);
  }
  return signals.map((signal) => coherenceChipHtml(signal, row)).join('');
}

function coherenceChipHtml(signal, row) {
  const known = signal === 'coherent' || Boolean(COHERENCE_SIGNALS[signal]);
  const def = signal === 'coherent'
    ? COHERENCE_OK_SIGNAL
    : COHERENCE_SIGNALS[signal] || { label: signal, icon: '' };
  let label = def.label;
  let title = '';
  if (signal === 'en_erreur' && row && row.error_message) {
    // The retry detail is visible (truncated), in the accessible name,
    // and complete in the title — never color or title alone.
    const detail = coherenceTruncateText(row.error_message, 40);
    label = `en erreur : ${detail}`;
    title = ` title="${escapeHtml(row.error_message)}"`;
  }
  return `
      <span class="coherence-chip coherence-chip-${known ? signal : 'unknown'}"${title}
            aria-label="${escapeHtml(label)}">
        ${def.icon}
        ${escapeHtml(label)}
      </span>
    `;
}

// Composed table row (2.6 extraction): the trigger, the entity link
// (CAP-8), type and chips, plus the expansion carried by
// coherenceRowExpansionHtml — pure over the payload + the volatile
// state, like the rest of the composition.
function coherenceRowHtml(row, expandedId, narrow) {
  const type = coherenceType(row);
  // CAP-8 : l'entité est un lien texte inline vers la surface
  // standard HA — inerte « aucune entité » quand il n'y en a pas.
  const entity = coherenceEntityLinkHtml(row.entity_id);
  const detail = coherenceRowExpansionHtml(row, expandedId, narrow);
  return `
      <tr${detail.rowClass}>
        <td class="coherence-id" data-label="Périphérique">
          ${detail.trigger}
        </td>
        <td data-label="Nom">${escapeHtml(row.name || '')}</td>
        <td class="ha-entity" data-label="Entité HA">${entity}</td>
        <td data-label="Type / sous-type">${escapeHtml(type)}</td>
        <td data-label="Statut">
          <div class="coherence-chips">${coherenceChipsHtml(row)}</div>
        </td>
      </tr>
      ${detail.expansion}
    `;
}

class EedomusConfigPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._hass = null;
    this._config = {};
    this._tab = 'peripheriques';
    this._periphs = null;
    this._error = null;
    this._search = '';
    this._touchedOnly = false;
    // Result-count announcements (sweep): one debounce timer per status
    // element id — a keystroke burst collapses into a single announce.
    this._statusAnnounceTimers = {};
    this._pendingRuleUsageId = null;
    this._boundHashChange = () => this._onHashChange();
    // Regles tab state (P.1.4)
    this._mapping = null;
    this._mappingError = null;
    this._ruleForm = null;
    this._rulesStatus = '';
    this._saveState = null; // null | 'saving' | 'applying' | {applied:{...}} | {error}
    this._validation = { valid: false, message: '' };
    this._confirmDelete = null;
    this._validateTimer = null;
    // YAML mode state (P.1.5)
    this._rulesMode = 'form'; // 'form' | 'yaml'
    this._yamlText = null;
    this._yamlError = null; // {message, line}
    this._yamlValidated = null; // last validated config
    this._yamlTimer = null;
    // Historique tab state (P.1.6)
    this._versions = null;
    this._currentMapping = null;
    this._versionsError = null;
    this._confirmRestore = null;
    this._historyStatus = '';
    // Coherence tab state (ticket 2.2)
    this._coherence = null;
    this._coherenceError = null;
    this._coherenceLoading = false;
    // Coherence interactions (ticket 2.3) — volatile per tab, like the
    // rest of the panel: filter, view and sort survive re-renders but are
    // never persisted between sessions.
    this._coherenceSearch = '';
    this._coherenceView = 'all'; // 'all' | 'to_verify'
    this._coherenceSort = { key: null, dir: null }; // dir: 'asc' | 'desc'
    // Coherence popover (ticket 2.4) — the panel's single floating
    // surface. One instance at most; its content renders from the
    // already-loaded row (no network call on open).
    this._coherencePopover = null; // open popover element
    this._coherencePopoverTrigger = null; // trigger to return focus to
    this._coherencePopoverByHover = false; // hover-opened, never focused
    this._coherenceHoverTimer = null; // hover intent delay
    this._coherenceHoverTrigger = null; // trigger the delay is for
    this._coherenceLeaveTimer = null; // grace crossing the anchor gap
    this._coherenceDismiss = null; // outside click/scroll/resize listener
    this._coherenceFocusOut = null; // focusout listener while open
    // Mobile expanded row (ticket 2.5) — the touch counterpart of
    // the popover, same trigger. One line expanded at most; the key
    // survives tbody re-renders as long as the row stays visible.
    this._coherenceExpandedId = null;
    this._boundCoherenceBreakpoint = (ev) => this._onCoherenceBreakpoint(ev);
  }

  set hass(hass) {
    this._hass = hass;
    if (this._built) {
      this._loadPeripherals();
      // Direct #coherence entry: the tab rendered before hass was assigned,
      // so its lazy load bailed out — start it now.
      if (this._tab === 'coherence' && this._coherence === null && !this._coherenceError) {
        this._loadCoherence();
      }
    }
  }

  get hass() {
    return this._hass;
  }

  setConfig(config) {
    this._config = config || {};
    if (this._hass) {
      this._render();
    }
  }

  connectedCallback() {
    this._tab = this._tabFromLocation();
    this._render();
    window.addEventListener('hashchange', this._boundHashChange);
    // Crossing the 900 px boundary swaps the detail surface: the
    // expanded-row state is dropped on the wide side (popover only).
    // Legacy browsers without MQL addEventListener use addListener.
    const narrowMedia = coherenceNarrowMedia();
    if (narrowMedia) {
      if (narrowMedia.addEventListener) {
        narrowMedia.addEventListener('change', this._boundCoherenceBreakpoint);
      } else if (narrowMedia.addListener) {
        narrowMedia.addListener(this._boundCoherenceBreakpoint);
      }
    }
    if (this._hass) {
      this._loadPeripherals();
    }
  }

  disconnectedCallback() {
    window.removeEventListener('hashchange', this._boundHashChange);
    const narrowMedia = coherenceNarrowMedia();
    if (narrowMedia) {
      if (narrowMedia.removeEventListener) {
        narrowMedia.removeEventListener(
          'change', this._boundCoherenceBreakpoint
        );
      } else if (narrowMedia.removeListener) {
        narrowMedia.removeListener(this._boundCoherenceBreakpoint);
      }
    }
    // Tears down the popover and its document-level listeners — the
    // mobile expanded state is just as volatile.
    this._closeCoherencePopover();
    this._coherenceExpandedId = null;
    // Pending debounced announcements never fire on a detached panel.
    for (const statusId of Object.keys(this._statusAnnounceTimers)) {
      clearTimeout(this._statusAnnounceTimers[statusId]);
    }
    this._statusAnnounceTimers = {};
  }

  _tabFromLocation() {
    const hash = window.location.hash.replace('#', '');
    return TABS.includes(hash) ? hash : 'peripheriques';
  }

  _onHashChange() {
    // Back/forward between tabs: the URL hash is the source of truth.
    const tab = this._tabFromLocation();
    if (tab !== this._tab) {
      this._tab = tab;
      // The replaced table carries no anchor row: like the popover,
      // a stale expanded row never survives the switch.
      this._coherenceExpandedId = null;
      this._renderTabContent();
    }
  }

  _setTab(tab, updateHash = true) {
    this._tab = tab;
    if (updateHash) {
      window.location.hash = tab;
    }
    this._renderTabContent();
  }

  async _loadPeripherals() {
    if (!this._hass || this._loading) {
      return;
    }
    this._loading = true;
    this._error = null;
    this._periphs = null;
    this._renderPeriphList();
    try {
      const result = await this._hass.callWS({
        type: 'eedomus/get_peripherals',
      });
      this._periphs = (result && result.peripherals) || [];
    } catch (err) {
      this._error = (err && (err.message || err.code)) || 'commande refusée';
    }
    this._loading = false;
    this._renderPeriphList();
  }

  _filteredPeriphs() {
    if (!this._periphs) {
      return null;
    }
    let rows = this._periphs;
    if (this._touchedOnly) {
      rows = rows.filter((row) => row.modified);
    }
    if (this._search) {
      const q = this._search.toLowerCase();
      rows = rows.filter(
        (row) =>
          (row.name || '').toLowerCase().includes(q) ||
          (row.usage_id || '').toLowerCase().includes(q)
      );
    }
    return rows;
  }

  _render() {
    if (!this.shadowRoot) {
      return;
    }
    this._built = true;
    this.shadowRoot.innerHTML = `
      <style>
        :host { box-sizing: border-box; }
        * { box-sizing: border-box; }
        .panel {
          max-width: 1040px; margin: 0 auto;
          padding: 8px 16px 48px;
          color: var(--primary-text-color);
          font-size: 14px;
          line-height: 1.5;
        }
        .panel-header {
          display: flex; align-items: center; justify-content: space-between;
          padding: 8px 0 16px;
          border-bottom: 1px solid var(--divider-color);
        }
        .panel-header h1 { font-size: 20px; font-weight: 400; margin: 0; }

        .tabs { display: flex; gap: 8px; padding: 12px 0 20px; }
        .tab {
          min-height: 44px; padding: 10px 20px; cursor: pointer;
          font: inherit; text-decoration: none;
          color: var(--secondary-text-color);
          background: transparent;
          border: none;
          border-bottom: 3px solid transparent;
        }
        .tab[aria-selected="true"] {
          color: var(--primary-text-color);
          font-weight: 500;
          border-bottom-color: var(--primary-color);
        }
        .tab:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }

        .toolbar { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-bottom: 8px; }
        .search {
          flex: 1 1 320px;
          display: flex; align-items: center; gap: 8px;
          background: var(--input-fill-color, var(--card-background-color));
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 12px);
          padding: 0 12px; min-height: 44px;
        }
        .search svg { flex: none; color: var(--secondary-text-color); }
        .search input {
          flex: 1; border: none; background: transparent;
          color: var(--primary-text-color); font: inherit; min-height: 42px;
        }
        .search input:focus-visible { outline: none; }
        .search:focus-within { outline: 2px solid var(--primary-color); }

        .filter-touches {
          display: inline-flex; align-items: center; gap: 8px;
          font: inherit; min-height: 44px; padding: 0 16px; cursor: pointer;
          color: var(--primary-text-color);
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: 9999px;
        }
        .filter-touches[aria-pressed="true"] {
          border-color: var(--primary-color);
          font-weight: 500;
        }
        .filter-touches .count { color: var(--secondary-text-color); }
        .filter-touches:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }

        .result-count { color: var(--secondary-text-color); font-size: 13px; margin: 0 0 12px; }

        .periph-list { display: flex; flex-direction: column; gap: 8px; }
        .periph-row {
          display: grid;
          grid-template-columns: 1.4fr 0.6fr 1.6fr 1fr auto auto;
          gap: 16px; align-items: center;
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 12px);
          padding: 12px 16px;
        }
        .periph-name { font-weight: 500; }
        .periph-meta { color: var(--secondary-text-color); font-size: 13px; }
        .periph-meta code, .mapping-meta {
          font-family: var(--code-font-family, ui-monospace, Menlo, monospace);
          font-size: 12.5px;
        }
        .periph-mapping .mapping-meta {
          color: var(--secondary-text-color); display: block; font-size: 13px;
        }
        .ha-entity {
          font-family: var(--code-font-family, ui-monospace, Menlo, monospace);
          font-size: 12.5px; word-break: break-all;
        }

        .badge-modified {
          display: inline-flex; align-items: center; gap: 6px;
          background: var(--accent-color);
          color: var(--text-accent-color, #fff);
          border-radius: 9999px;
          padding: 3px 10px;
          font-size: 12px; font-weight: 500;
          white-space: nowrap; cursor: help;
        }
        .badge-modified .dot {
          width: 6px; height: 6px; border-radius: 9999px;
          background: var(--text-accent-color, #fff);
        }

        .row-action {
          font: inherit; font-size: 13px; cursor: pointer;
          min-height: 44px; padding: 8px 14px;
          color: var(--primary-text-color);
          background: transparent;
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 12px);
          white-space: nowrap;
        }
        .row-action:hover { background: var(--input-fill-color, var(--card-background-color)); }
        .row-action:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }

        .sr-only {
          position: absolute; width: 1px; height: 1px;
          overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap;
        }

        .state-message {
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 12px);
          padding: 24px;
          color: var(--secondary-text-color);
          text-align: center;
        }
        .state-message .retry {
          font: inherit; min-height: 44px; margin-top: 12px;
          padding: 8px 20px; cursor: pointer;
          color: var(--primary-text-color);
          background: transparent;
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 12px);
        }
        .state-message .retry:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }

        .skeleton-row {
          height: 64px;
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 12px);
          opacity: 0.6;
        }

        .placeholder { color: var(--secondary-text-color); }
        .placeholder code {
          font-family: var(--code-font-family, ui-monospace, Menlo, monospace);
        }

        .rule-form {
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 12px);
          padding: 16px;
          display: flex; flex-direction: column; gap: 12px;
          max-width: 760px;
        }
        .form-field { display: flex; flex-direction: column; gap: 4px; }
        .form-field label {
          color: var(--primary-text-color); font-size: 13px; font-weight: 500;
        }
        .form-field input, .form-field select {
          font: inherit; color: var(--primary-text-color);
          background: var(--input-fill-color, var(--card-background-color));
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 12px);
          min-height: 44px; padding: 8px 12px;
        }
        .form-field input:focus-visible, .form-field select:focus-visible {
          outline: 2px solid var(--primary-color); outline-offset: 2px;
        }
        .form-field input[aria-invalid="true"] {
          border-color: var(--error-color, #db4437);
        }
        .form-hint { color: var(--secondary-text-color); font-size: 12.5px; }
        .form-validation {
          color: var(--error-color, #db4437);
          font-size: 13px; margin: 0; min-height: 20px;
        }
        .form-actions { display: flex; gap: 12px; flex-wrap: wrap; }
        .rule-save[disabled] { opacity: 0.5; cursor: not-allowed; }

        .mode-toggle { display: inline-flex; gap: 0; margin-bottom: 8px; }
        .mode-toggle button {
          font: inherit; font-size: 13px; cursor: pointer;
          min-height: 44px; padding: 8px 18px;
          color: var(--primary-text-color);
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
        }
        .mode-toggle button:first-child {
          border-radius: var(--ha-card-border-radius, 12px) 0 0 var(--ha-card-border-radius, 12px);
        }
        .mode-toggle button:last-child {
          border-radius: 0 var(--ha-card-border-radius, 12px) var(--ha-card-border-radius, 12px) 0;
          border-left: none;
        }
        .mode-toggle button[aria-pressed="true"] {
          color: var(--text-accent-color, #fff);
          background: var(--primary-color);
          border-color: var(--primary-color);
        }
        .mode-toggle button:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }

        .yaml-editor-wrap {
          position: relative;
          display: flex;
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 12px);
          overflow: hidden;
        }
        .yaml-editor-wrap:focus-within { outline: 2px solid var(--primary-color); }
        .yaml-gutter {
          flex: none; padding: 12px 8px 12px 12px;
          text-align: right; user-select: none;
          color: var(--secondary-text-color);
          background: var(--input-fill-color, var(--card-background-color));
          font-family: var(--code-font-family, ui-monospace, Menlo, monospace);
          font-size: 12.5px; line-height: 1.5;
          white-space: pre;
          border-right: 1px solid var(--divider-color);
        }
        .yaml-code-area { position: relative; flex: 1; min-width: 0; }
        .yaml-highlight {
          position: absolute; inset: 0;
          margin: 0; padding: 12px;
          font-family: var(--code-font-family, ui-monospace, Menlo, monospace);
          font-size: 12.5px; line-height: 1.5;
          white-space: pre; overflow: auto;
          color: var(--primary-text-color);
          pointer-events: none;
        }
        .yaml-editor {
          position: relative;
          display: block; width: 100%;
          min-height: 420px;
          margin: 0; padding: 12px;
          border: none; resize: vertical;
          background: transparent;
          color: transparent; caret-color: var(--primary-text-color);
          font-family: var(--code-font-family, ui-monospace, Menlo, monospace);
          font-size: 12.5px; line-height: 1.5;
          white-space: pre; overflow-wrap: normal; overflow: auto;
        }
        .yaml-editor:focus-visible { outline: none; }
        .yaml-highlight .tok-key { color: var(--primary-color); }
        .yaml-highlight .tok-str { color: var(--success-color, #43a047); }
        .yaml-highlight .tok-num { color: var(--warning-color, #ff9800); }
        .yaml-highlight .tok-bool { color: var(--warning-color, #ff9800); }
        .yaml-highlight .tok-comment { color: var(--secondary-text-color); font-style: italic; }

        .version-card {
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 12px);
          padding: 14px 16px;
          margin-bottom: 12px;
        }
        .version-head {
          display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
        }
        .version-title { font-weight: 500; }
        .version-meta { color: var(--secondary-text-color); font-size: 13px; }
        .version-active {
          display: inline-block;
          background: var(--primary-color);
          color: var(--text-accent-color, #fff);
          border-radius: 9999px;
          padding: 2px 10px;
          font-size: 12px; font-weight: 500;
        }
        .diff {
          margin: 12px 0 0;
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 12px);
          overflow: auto;
          max-height: 320px;
          font-family: var(--code-font-family, ui-monospace, Menlo, monospace);
          font-size: 12.5px; line-height: 1.45;
        }
        .diff-line {
          display: flex; gap: 8px; padding: 1px 10px 1px 6px;
          white-space: pre;
          color: var(--primary-text-color);
        }
        .diff-line .prefix {
          flex: none; width: 14px; text-align: center;
          color: var(--secondary-text-color);
        }
        .diff-line .content { flex: 1; }
        .diff-line-added {
          background: color-mix(in srgb, var(--success-color, #43a047) 16%, transparent);
          border-left: 3px solid var(--success-color, #43a047);
        }
        .diff-line-removed {
          background: color-mix(in srgb, var(--error-color, #db4437) 16%, transparent);
          border-left: 3px solid var(--error-color, #db4437);
        }
        .diff-line-modified {
          background: color-mix(in srgb, var(--warning-color, #ff9800) 16%, transparent);
          border-left: 3px solid var(--warning-color, #ff9800);
        }

        .coherence-table-wrap {
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 12px);
          background: var(--card-background-color);
          overflow: auto;
          max-height: 70vh;
        }
        .coherence-table { width: 100%; border-collapse: collapse; }
        .coherence-table th {
          position: sticky; top: 0; z-index: 1;
          background: var(--card-background-color);
          color: var(--secondary-text-color);
          font-weight: 500; text-align: left;
          padding: 12px 16px; white-space: nowrap;
          border-bottom: 1px solid var(--divider-color);
        }
        .sort-header {
          display: inline-flex; align-items: center; gap: 4px;
          font: inherit; font-size: 13px; cursor: pointer;
          color: inherit; background: transparent; border: none;
          padding: 0; text-align: left; white-space: nowrap;
        }
        .sort-header:focus-visible {
          outline: 2px solid var(--primary-color); outline-offset: 2px;
        }
        .sort-arrow { color: var(--secondary-text-color); display: inline-flex; }
        .coherence-table td {
          padding: 12px 16px;
          border-bottom: 1px solid var(--divider-color);
          vertical-align: top;
          word-break: break-word;
        }
        .coherence-table tbody tr:last-child td { border-bottom: none; }
        .coherence-table .coherence-id code {
          font-family: var(--code-font-family, ui-monospace, Menlo, monospace);
          font-size: 12.5px;
        }
        .coherence-chips { display: flex; flex-wrap: wrap; gap: 8px; }
        .coherence-chip {
          display: inline-flex; align-items: center; gap: 6px;
          padding: 4px 12px;
          border-radius: 9999px;
          font-size: 12.5px;
          color: var(--primary-text-color);
          white-space: nowrap;
        }
        .coherence-chip svg { flex: none; }
        .coherence-chip-sans_entite {
          background: var(--card-background-color);
          background: color-mix(in srgb, var(--error-color, #db4437) 12%, var(--card-background-color));
        }
        .coherence-chip-sans_entite svg { color: var(--error-color, #db4437); }
        .coherence-chip-douteux {
          background: var(--card-background-color);
          background: color-mix(in srgb, var(--warning-color, #ff9800) 12%, var(--card-background-color));
        }
        .coherence-chip-douteux svg { color: var(--warning-color, #ff9800); }
        .coherence-chip-regle_active {
          background: var(--card-background-color);
          background: color-mix(in srgb, var(--primary-color) 12%, var(--card-background-color));
        }
        .coherence-chip-regle_active svg { color: var(--primary-color); }
        .coherence-chip-en_erreur {
          background: var(--card-background-color);
          background: color-mix(in srgb, var(--error-color, #db4437) 12%, var(--card-background-color));
        }
        .coherence-chip-en_erreur svg { color: var(--error-color, #db4437); }
        .coherence-chip-coherent {
          background: var(--card-background-color);
          background: color-mix(in srgb, var(--success-color, #43a047) 12%, var(--card-background-color));
        }
        .coherence-chip-coherent svg { color: var(--success-color, #43a047); }
        .coherence-chip-unknown {
          background: var(--input-fill-color, var(--card-background-color));
          background: color-mix(in srgb, var(--secondary-text-color) 12%, var(--card-background-color));
        }

        .coherence-id-trigger {
          font: inherit; padding: 0; border: none; background: transparent;
          color: inherit; cursor: pointer;
          text-decoration: underline dotted var(--secondary-text-color);
          text-underline-offset: 3px;
        }
        .coherence-id-trigger[aria-expanded="true"] {
          text-decoration-style: solid;
        }
        .coherence-id-trigger:focus-visible {
          outline: 2px solid var(--primary-color); outline-offset: 2px;
        }

        /* Lien entité (2.6, CAP-8) : lien texte inline — accent,
           souligné, jamais un chrome de bouton ; distinct du
           déclencheur popover (pointillé). */
        .entity-link {
          color: var(--primary-color);
          text-decoration: underline;
          text-underline-offset: 3px;
        }
        .entity-link:focus-visible {
          outline: 2px solid var(--primary-color); outline-offset: 2px;
        }

        /* Popover: the panel's single floating surface (DESIGN.md
           §Elevation & Depth) — card background, divider filet, theme
           card radius and shadow; no invented elevation. */
        .periph-popover {
          position: fixed; z-index: 5;
          width: min(400px, calc(100vw - 16px));
          max-height: min(70vh, 480px);
          overflow: auto;
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 12px);
          box-shadow: var(--ha-card-box-shadow, none);
          padding: 16px;
        }
        .popover-head {
          display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap;
        }
        .popover-name { font-weight: 500; }
        .popover-id {
          font-family: var(--code-font-family, ui-monospace, Menlo, monospace);
          font-size: 12.5px; color: var(--secondary-text-color);
        }
        .popover-section {
          border-top: 1px solid var(--divider-color);
          margin-top: 12px; padding-top: 12px;
        }
        .popover-heading {
          margin: 0 0 8px; font-size: 12px; font-weight: 500;
          color: var(--secondary-text-color);
          text-transform: uppercase; letter-spacing: 0.5px;
        }
        .popover-error {
          color: var(--error-color, #db4437);
          font-size: 13px; margin: 0 0 8px;
        }
        .detail-row { display: flex; gap: 12px; padding: 2px 0; }
        .detail-row dt {
          flex: 0 0 38%; color: var(--secondary-text-color); font-size: 12.5px;
        }
        .detail-row dd { margin: 0; flex: 1; min-width: 0; word-break: break-word; }
        .detail-code {
          font-family: var(--code-font-family, ui-monospace, Menlo, monospace);
          font-size: 12.5px;
        }
        .detail-unknown { color: var(--secondary-text-color); }
        .popover-actions {
          display: flex; flex-wrap: wrap; gap: 8px;
          margin-top: 12px;
        }
        .popover-raw {
          border-top: 1px solid var(--divider-color);
          margin-top: 12px; padding-top: 4px;
        }
        .popover-raw summary {
          cursor: pointer; color: var(--secondary-text-color);
          display: flex; align-items: center; min-height: 44px; font-size: 13px;
        }
        .popover-raw summary:focus-visible {
          outline: 2px solid var(--primary-color); outline-offset: 2px;
        }
        .popover-raw .detail-row dt { flex: 0 0 45%; }

        .skeleton-cell {
          height: 18px;
          border-radius: 9999px;
          background: var(--input-fill-color, var(--card-background-color));
          opacity: 0.6;
        }

        /* The COHERENCE_NARROW_PX constant (JS surface switch of
           ticket 2.5, coherenceNarrowView) — one breakpoint, two
           surfaces: this reflow and the tap-vs-popover switch. */
        @media (max-width: ${COHERENCE_NARROW_PX}px) {
          .periph-row {
            display: flex; flex-direction: column; align-items: stretch; gap: 8px;
          }
          .row-top { display: flex; align-items: center; gap: 8px; }
          .row-top .periph-identity { flex: 1; }
          .row-top .periph-meta { display: block; }
          .periph-mapping { border-top: 1px solid var(--divider-color); padding-top: 8px; }
          .row-action { width: 100%; }

          /* The sort headers stay operable on mobile: the thead becomes a
             sticky wrapping bar of sort buttons, still collant au
             défilement. */
          .coherence-table thead {
            display: flex; flex-wrap: wrap; gap: 8px;
            position: sticky; top: 0; z-index: 1;
            padding: 8px 16px;
            background: var(--card-background-color);
            border-bottom: 1px solid var(--divider-color);
          }
          .coherence-table thead tr { display: contents; }
          .coherence-table thead th {
            display: block; position: static;
            padding: 0; border-bottom: none; white-space: normal;
          }
          .sort-header { min-height: 44px; }
          .coherence-table, .coherence-table tbody,
          .coherence-table tr, .coherence-table td {
            display: block; width: 100%;
          }
          .coherence-table tr {
            padding: 12px 16px;
            border-bottom: 1px solid var(--divider-color);
          }
          .coherence-table tbody tr:last-child { border-bottom: none; }
          .coherence-table td {
            padding: 0 0 8px;
            border-bottom: none;
          }
          .coherence-table td[data-label]::before {
            content: attr(data-label);
            display: block;
            color: var(--secondary-text-color);
            font-size: 12px;
          }

          /* Ligne étendue (2.5) : parité de contenu avec le popover,
             surface différente — la paire ligne + extension lit comme
             une seule unité au doigt, l'extension vit dans le reflow
             bloc (jamais de scroll horizontal silencieux). */
          .coherence-id-trigger {
            display: inline-flex; align-items: center;
            min-height: 44px;
          }
          .entity-link {
            display: inline-flex; align-items: center;
            min-height: 44px;
          }
          .coherence-table tr.coherence-row-expanded {
            padding-bottom: 0;
            border-bottom: none;
          }
          .coherence-table tr.coherence-expanded-row {
            padding-top: 0;
            border-top: none;
          }
          .coherence-table tr.coherence-expanded-row td { padding: 0; }
          .coherence-expanded-body {
            border-top: 1px solid var(--divider-color);
            padding-top: 12px;
          }
        }
      </style>

      <div class="panel">
        <header class="panel-header">
          <h1>Eedomus Config</h1>
        </header>

        <nav class="tabs" aria-label="Sections du panneau">
          <button class="tab" role="tab" data-tab="peripheriques" aria-selected="false">Périphériques</button>
          <button class="tab" role="tab" data-tab="regles" aria-selected="false">Règles</button>
          <button class="tab" role="tab" data-tab="historique" aria-selected="false">Historique</button>
          <button class="tab" role="tab" data-tab="coherence" aria-selected="false">Cohérence</button>
        </nav>

        <main id="tab-content" aria-live="polite"></main>
      </div>
    `;

    this.shadowRoot.addEventListener('click', (ev) => this._onClick(ev));
    this.shadowRoot.addEventListener('auxclick', (ev) => this._onAuxClick(ev));
    this.shadowRoot.addEventListener('input', (ev) => this._onInput(ev));
    this.shadowRoot.addEventListener('keydown', (ev) => this._onKeyDown(ev));
    this.shadowRoot.addEventListener(
      'mouseover', (ev) => this._onCoherenceMouseOver(ev)
    );
    this.shadowRoot.addEventListener(
      'mouseout', (ev) => this._onCoherenceMouseOut(ev)
    );

    this._renderTabContent();
  }

  _onClick(ev) {
    const tab = ev.target.closest('.tab');
    if (tab) {
      this._setTab(tab.dataset.tab);
      return;
    }
    const retry = ev.target.closest('.retry');
    if (retry && retry.dataset.retry !== 'mapping') {
      if (retry.dataset.retry === 'versions') {
        this._versionsError = null;
        this._loadVersions();
      } else if (retry.dataset.retry === 'coherence') {
        this._coherenceError = null;
        this._loadCoherence();
      } else {
        this._loadPeripherals();
      }
      return;
    }
    const coherenceViewBtn = ev.target.closest('[data-coherence-view]');
    if (coherenceViewBtn) {
      this._coherenceView =
        this._coherenceView === 'to_verify' ? 'all' : 'to_verify';
      this._renderCoherenceTable();
      return;
    }
    const sortHeader = ev.target.closest('[data-sort-key]');
    if (sortHeader) {
      this._coherenceSortBy(sortHeader.dataset.sortKey);
      return;
    }
    const coherenceShowAll = ev.target.closest('[data-coherence-show-all]');
    if (coherenceShowAll) {
      this._coherenceView = 'all';
      this._renderCoherenceTable();
      return;
    }
    const popoverTrigger = ev.target.closest('[data-coherence-popover]');
    if (popoverTrigger) {
      this._cancelCoherenceHover();
      if (coherenceNarrowView()) {
        // Sous 900 px (2.5) : le tap étend la ligne — le popover de
        // 2.4 reste une surface desktop, le hover gating est intact.
        this._toggleCoherenceExpanded(
          popoverTrigger.dataset.coherencePopover
        );
        return;
      }
      // Entrée/click on the periph_id cell: open without the hover
      // delay; clicking the open trigger toggles it closed.
      if (this._coherencePopoverTrigger === popoverTrigger) {
        this._closeCoherencePopover();
      } else {
        this._openCoherencePopover(popoverTrigger, { focusPopover: true });
      }
      return;
    }
    const entityLink = ev.target.closest('[data-entity-id]');
    if (entityLink) {
      // CAP-8 : le lien entité navigue vers la surface standard HA —
      // jamais le popover ni l'extension (stopPropagation), et le
      // href="#" de repli ne touche jamais le hash du panneau.
      ev.preventDefault();
      ev.stopPropagation();
      this._openEntityMoreInfo(entityLink.dataset.entityId);
      return;
    }
    const filterBtn = ev.target.closest('.filter-touches');
    if (filterBtn) {
      this._touchedOnly = !this._touchedOnly;
      this._renderPeriphList();
      return;
    }
    const action = ev.target.closest('.row-action');
    if (action && action.dataset.periphId !== undefined) {
      this._createRuleFor(action.dataset.periphId, action.dataset.usageId);
      return;
    }
    if (this._tab === 'regles') {
      this._onRulesEvent(ev);
      return;
    }
    if (this._tab === 'historique') {
      const restoreBtn = ev.target.closest('[data-restore]');
      if (restoreBtn) {
        this._restoreVersion(parseInt(restoreBtn.dataset.restore, 10));
      }
    }
  }

  _onAuxClick(ev) {
    // Middle-click / « ouvrir dans un nouvel onglet » sur le href="#"
    // de repli : le lien entité ne navigue jamais par lui-même —
    // seule la surface standard HA (hass-more-info) s'ouvre, et le
    // hash du panneau reste intact.
    if (ev.target.closest && ev.target.closest('[data-entity-id]')) {
      ev.preventDefault();
    }
  }

  _onInput(ev) {
    if (ev.target.id === 'periph-search') {
      this._search = ev.target.value;
      // Visual filtering is real-time; only the live-region
      // announcement is debounced (sweep) — one announce per typing
      // burst, not one per character.
      this._renderPeriphList({ announceStatus: false });
      this._debounceStatusAnnounce(
        'periph-status-live', () => this._announcePeriphStatus()
      );
    } else if (ev.target.id === 'coherence-search') {
      this._coherenceSearch = ev.target.value;
      this._renderCoherenceTable({ announceStatus: false });
      this._debounceStatusAnnounce(
        'coherence-status-live', () => this._announceCoherenceStatus()
      );
    } else if (ev.target.id === 'yaml-editor') {
      this._yamlText = ev.target.value;
      this._renderYamlHighlight();
      this._yamlValidated = null;
      this._yamlError = null;
      this._updateYamlState();
      this._scheduleYamlValidation();
    } else if (this._tab === 'regles') {
      this._onRulesInput(ev);
    }
  }

  _onKeyDown(ev) {
    if (ev.key === 'Escape') {
      if (this._coherencePopover) {
        // Échap referme le popover (le popover intercepte déjà l'Échap
        // quand il détient le focus — cette branche est le filet pour
        // un popover ouvert au survol, jamais focalisé). Sans le focus
        // dedans, l'Échap poursuit vers le champ actif : vider la
        // recherche doit continuer de fonctionner.
        const pop = this._coherencePopover;
        const active = this.shadowRoot.activeElement;
        this._closeCoherencePopover();
        if (pop.contains(active)) {
          return;
        }
      }
      if (this._coherenceExpandedId !== null) {
        // Échap referme aussi la ligne étendue mobile (même geste que
        // le popover, 2.5) : le focus revient au déclencheur quand il
        // opérait l'extension ; sinon l'Échap poursuit vers le champ
        // actif — vider la recherche reste fonctionnel (contrat 2.4).
        const id = this._coherenceExpandedId;
        const root = this.shadowRoot;
        const expandedRow = root
          ? root.getElementById(coherenceExpandedRowId(id))
          : null;
        const active = root ? root.activeElement : null;
        const onTrigger = ev.target && ev.target.closest
          ? ev.target.closest('[data-coherence-popover]')
          : null;
        const inside = Boolean(
          (expandedRow && active && expandedRow.contains(active)) ||
            (onTrigger && String(onTrigger.dataset.coherencePopover) === id)
        );
        this._coherenceExpandedId = null;
        this._renderCoherenceTable();
        if (inside) {
          const btn = this._coherenceTriggerFor(id);
          if (btn) {
            btn.focus();
          }
          return;
        }
      }
      if (ev.target.id === 'periph-search') {
        if (ev.target.value !== '') {
          this._search = '';
          ev.target.value = '';
          this._renderPeriphList();
        }
        ev.target.blur();
      } else if (ev.target.id === 'coherence-search') {
        if (this._coherenceSearch !== '') {
          this._coherenceSearch = '';
          ev.target.value = '';
          this._renderCoherenceTable();
        }
        ev.target.blur();
      } else if (ev.target.closest && ev.target.closest('.rule-form')) {
        // Escape cancels the rule form, content stays in the list.
        this._ruleForm = null;
        this._validation = { valid: false, message: '' };
        const content = this.shadowRoot.getElementById('tab-content');
        if (content) {
          content.innerHTML = this._renderRulesTab();
          this._wireRulesTab();
        }
      }
    }
  }

  _createRuleFor(periphId, usageId) {
    // Shortcut: switch to Règles with the usage_id pre-filled (P.1.4
    // consumes it in the rule form).
    this._pendingRuleUsageId = usageId;
    this._setTab('regles');
  }

  _renderTabContent() {
    const root = this.shadowRoot;
    if (!root) {
      return;
    }
    // A tab switch replaces the coherence table: the popover closes,
    // never survives detached from its anchor row — the mobile
    // expanded state is just as volatile.
    this._closeCoherencePopover();
    this._coherenceExpandedId = null;
    root.querySelectorAll('.tab').forEach((tab) => {
      tab.setAttribute('aria-selected', String(tab.dataset.tab === this._tab));
    });
    const content = root.getElementById('tab-content');
    if (!content) {
      return;
    }
    if (this._tab === 'peripheriques') {
      content.innerHTML = this._renderPeriphToolbar();
      this._renderPeriphList();
      if (this._periphs === null && !this._loading) {
        this._loadPeripherals();
      }
    } else if (this._tab === 'regles') {
      content.innerHTML = this._renderRulesTab();
      this._wireRulesTab();
      if (this._mapping === null && !this._mappingError) {
        this._loadMapping();
      }
    } else if (this._tab === 'historique') {
      content.innerHTML = this._renderHistoryTab();
      this._wireHistoryTab();
      if (this._versions === null && !this._versionsError) {
        this._loadVersions();
      }
    } else if (this._tab === 'coherence') {
      content.innerHTML = this._renderCoherenceTab();
      this._renderCoherenceTable();
      if (this._coherence === null && !this._coherenceError) {
        this._loadCoherence();
      }
    } else {
      content.innerHTML = `
        <p class="placeholder">
          Onglet inconnu.
        </p>
      `;
    }
  }

  // ================= Historique (P.1.6) =================

  async _loadVersions() {
    if (!this._hass) {
      return;
    }
    this._versionsError = null;
    try {
      const result = await this._hass.callWS({
        type: 'eedomus/get_mapping_versions',
      });
      this._versions = (result && result.versions) || [];
      this._currentMapping = (result && result.current) || {};
    } catch (err) {
      this._versionsError = (err && (err.message || err.code)) || 'commande refusée';
    }
    if (this._tab === 'historique') {
      const content = this.shadowRoot.getElementById('tab-content');
      if (content) {
        content.innerHTML = this._renderHistoryTab();
        this._wireHistoryTab();
      }
    }
  }

  _formatTimestamp(ts) {
    if (!ts) {
      return 'date inconnue';
    }
    // Storage format: 2026-09-28T09:19:00
    const [datePart, timePart] = String(ts).split('T');
    if (!timePart) {
      return datePart;
    }
    return `${datePart} ${timePart.slice(0, 5)}`;
  }

  _reasonLabel(reason) {
    if (reason === 'ingestion') {
      return 'édition manuelle du fichier';
    }
    if (reason === 'migration') {
      return 'migration de schéma';
    }
    return 'sauvegarde depuis le panneau';
  }

  _renderHistoryTab() {
    if (this._versionsError) {
      return `
        <div class="state-message" role="alert">
          Impossible de charger l'historique : ${this._escapeHtml(this._versionsError)}.
          <br>
          <button class="retry" type="button" data-retry="versions">Réessayer</button>
        </div>
      `;
    }
    if (this._versions === null) {
      return '<div class="skeleton-row"></div>'.repeat(3);
    }
    if (this._versions.length === 0) {
      return `
        <div class="state-message">
          Aucune sauvegarde encore. La première sauvegarde archivera la version
          courante.
        </div>
      `;
    }

    const statusHtml = `
      <p class="result-count" id="history-status" role="status"></p>
    `;

    const cards = [];
    // Current canonical mapping: the active state, not restorable on itself
    cards.push(`
      <div class="version-card">
        <div class="version-head">
          <span class="version-title">Configuration actuelle</span>
          <span class="version-active">actuelle</span>
          <span class="version-meta">en vigueur</span>
        </div>
      </div>
    `);
    // Archived versions, newest first, max three
    this._versions.slice(0, 3).forEach((version, index) => {
      const confirm = this._confirmRestore === index;
      const diffHtml =
        this._versions.length === 1
          ? '<p class="version-meta">Première version — le diff apparaîtra à la prochaine sauvegarde.</p>'
          : this._renderDiff(index);
      cards.push(`
        <div class="version-card">
          <div class="version-head">
            <span class="version-title">Version du ${this._escapeHtml(this._formatTimestamp(version.timestamp))}</span>
            <span class="version-meta">${this._escapeHtml(this._reasonLabel(version.reason))}</span>
            <button class="row-action" type="button" data-restore="${index}">
              ${confirm ? 'Confirmer la restauration ?' : 'Restaurer'}
            </button>
          </div>
          ${confirm ? `<p class="form-validation" role="alert">Restaurer la version du ${this._escapeHtml(this._formatTimestamp(version.timestamp))} ? Le mapping actuel sera archivé.</p>` : ''}
          ${diffHtml}
        </div>
      `);
    });

    return `${statusHtml}<div class="versions">${cards.join('')}</div>`;
  }

  _wireHistoryTab() {
    const status = this.shadowRoot.getElementById('history-status');
    if (status) {
      status.textContent = this._historyStatus;
    }
  }

  _renderDiff(index) {
    // Diff between the selected version and the previous (older) one
    const newer = this._versions[index];
    const older = this._versions[index + 1];
    const newText = this._yamlDumpFull(newer.config || {});
    const oldText = older ? this._yamlDumpFull(older.config || {}) : '';
    const ops = this._diffLines(oldText.split('\n'), newText.split('\n'));
    const html = ops
      .map((op) => {
        const cls = { added: 'diff-line-added', removed: 'diff-line-removed', modified: 'diff-line-modified' }[op.type];
        const prefix = { added: '+', removed: '-', modified: '~' }[op.type];
        if (!cls) {
          return `<div class="diff-line"><span class="prefix"> </span><span class="content">${this._escapeHtml(op.line)}</span></div>`;
        }
        return `<div class="diff-line ${cls}" aria-label="${op.type === 'added' ? 'ligne ajoutée' : op.type === 'removed' ? 'ligne supprimée' : 'ligne modifiée'}"><span class="prefix" aria-hidden="true">${prefix}</span><span class="content">${this._escapeHtml(op.line)}</span></div>`;
      })
      .join('');
    return `<div class="diff" tabindex="0" role="region" aria-label="Différences avec la version précédente">${html}</div>`;
  }

  _diffLines(a, b) {
    // Longest-common-subsequence line diff: O(n*m), fine for a mapping
    // document (a few hundred lines).
    const n = a.length;
    const m = b.length;
    const dp = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
    for (let i = n - 1; i >= 0; i--) {
      for (let j = m - 1; j >= 0; j--) {
        dp[i][j] =
          a[i] === b[j]
            ? dp[i + 1][j + 1] + 1
            : Math.max(dp[i + 1][j], dp[i][j + 1]);
      }
    }
    const raw = [];
    let i = 0;
    let j = 0;
    while (i < n && j < m) {
      if (a[i] === b[j]) {
        raw.push({ type: 'same', line: a[i] });
        i++;
        j++;
      } else if (dp[i + 1][j] >= dp[i][j + 1]) {
        raw.push({ type: 'removed', line: a[i] });
        i++;
      } else {
        raw.push({ type: 'added', line: b[j] });
        j++;
      }
    }
    while (i < n) {
      raw.push({ type: 'removed', line: a[i] });
      i++;
    }
    while (j < m) {
      raw.push({ type: 'added', line: b[j] });
      j++;
    }
    // A removed run followed by an added run contains the changed lines:
    // pairs whose key (the text before ':') matches become a modified
    // line; the rest stay honest additions/removals.
    const ops = [];
    const keyOf = (line) => {
      const idx = line.indexOf(':');
      return idx === -1 ? line.trim() : line.slice(0, idx).trim();
    };
    let k = 0;
    while (k < raw.length) {
      if (raw[k].type !== 'removed') {
        ops.push(raw[k]);
        k++;
        continue;
      }
      const removedRun = [];
      const addedRun = [];
      while (k < raw.length && raw[k].type === 'removed') {
        removedRun.push(raw[k]);
        k++;
      }
      while (k < raw.length && raw[k].type === 'added') {
        addedRun.push(raw[k]);
        k++;
      }
      const used = new Set();
      for (const rem of removedRun) {
        const p = addedRun.findIndex(
          (add, idx) => !used.has(idx) && keyOf(add.line) === keyOf(rem.line)
        );
        if (p !== -1) {
          used.add(p);
          ops.push({ type: 'modified', line: addedRun[p].line });
        } else {
          ops.push(rem);
        }
      }
      addedRun.forEach((add, idx) => {
        if (!used.has(idx)) {
          ops.push(add);
        }
      });
    }
    return ops;
  }

  async _restoreVersion(index) {
    const version = this._versions[index];
    if (!version || !this._hass) {
      return;
    }
    if (this._confirmRestore !== index) {
      // Two-gesture restore: first click asks for confirmation
      this._confirmRestore = index;
      const content = this.shadowRoot.getElementById('tab-content');
      content.innerHTML = this._renderHistoryTab();
      this._wireHistoryTab();
      return;
    }
    this._confirmRestore = null;
    this._historyStatus = 'Sauvegarde… puis Application…';
    const content = this.shadowRoot.getElementById('tab-content');
    if (content) {
      content.innerHTML = this._renderHistoryTab();
      this._wireHistoryTab();
    }
    const ok = await this._persistMapping(version.config || {});
    if (ok) {
      this._historyStatus = `Version du ${this._formatTimestamp(version.timestamp)} restaurée. Le mapping remplacé est archivé.`;
      this._versions = null;
      await this._loadVersions();
    } else {
      this._historyStatus = 'Échec de la restauration. Le mapping courant est conservé.';
    }
    const status = this.shadowRoot.getElementById('history-status');
    if (status) {
      status.textContent = this._historyStatus;
    }
  }

  // ================= Cohérence (ticket 2.2) =================

  async _loadCoherence() {
    if (!this._hass || this._coherenceLoading) {
      return;
    }
    this._coherenceLoading = true;
    this._coherenceError = null;
    this._coherence = null;
    if (this._tab === 'coherence') {
      const content = this.shadowRoot.getElementById('tab-content');
      if (content) {
        // Retry shows the loading state again, never a stale table/error.
        content.innerHTML = this._renderCoherenceTab();
      }
    }
    try {
      const result = await this._hass.callWS({
        type: 'eedomus/get_coherence',
      });
      this._coherence = (result && result.peripherals) || [];
    } catch (err) {
      this._coherenceError = (err && (err.message || err.code)) || 'commande refusée';
    }
    this._coherenceLoading = false;
    if (this._tab === 'coherence') {
      const content = this.shadowRoot.getElementById('tab-content');
      if (content) {
        content.innerHTML = this._renderCoherenceTab();
        this._renderCoherenceTable();
      }
    }
  }

  _renderCoherenceTab() {
    if (this._coherenceError) {
      return `
        <div class="state-message" role="alert">
          Impossible de charger la cohérence : ${this._escapeHtml(this._coherenceError)}.
          <br>
          <button class="retry" type="button" data-retry="coherence">Réessayer</button>
        </div>
      `;
    }
    if (this._coherence === null) {
      return this._renderCoherenceSkeleton();
    }
    if (this._coherence.length === 0) {
      return `
        <div class="state-message">
          Aucun périphérique détecté. Vérifiez que la box eedomus est
          joignable et que l'intégration est configurée.
        </div>
      `;
    }
    return `
      ${this._renderCoherenceToolbar()}
      <p class="result-count" id="coherence-status"></p>
      <p class="sr-only" id="coherence-status-live" role="status"></p>
      <div id="coherence-body"></div>
    `;
  }

  _renderCoherenceToolbar() {
    const toVerify = (this._coherence || []).filter(coherenceToVerify).length;
    return `
      <div class="toolbar">
        <div class="search">
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M15.5 14h-.79l-.28-.27a6.5 6.5 0 1 0-.7.7l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0A4.5 4.5 0 1 1 14 9.5 4.5 4.5 0 0 1 9.5 14z"/></svg>
          <input id="coherence-search" type="search"
                 placeholder="Rechercher par nom ou periph_id"
                 aria-label="Rechercher un périphérique par nom ou periph_id"
                 value="${this._escapeHtml(this._coherenceSearch)}">
        </div>
        <button class="filter-touches" type="button" data-coherence-view="to_verify"
                aria-pressed="${this._coherenceView === 'to_verify'}">
          À vérifier <span class="count">(${toVerify})</span>
        </button>
      </div>
    `;
  }

  // Result-count announcements (sweep). The visible count element
  // updates with every render (it must never lag the filtering); only
  // the sr-only live region is debounced, so a typing burst yields
  // one announcement from the same pure message helper as the render.
  _cancelStatusAnnounce(statusId) {
    if (statusId && this._statusAnnounceTimers[statusId]) {
      clearTimeout(this._statusAnnounceTimers[statusId]);
      delete this._statusAnnounceTimers[statusId];
    }
  }

  _debounceStatusAnnounce(statusId, announce) {
    // One shared timer per live region, cancelled on every keystroke:
    // a typing burst collapses into a single post-pause announcement.
    this._cancelStatusAnnounce(statusId);
    this._statusAnnounceTimers[statusId] = setTimeout(() => {
      delete this._statusAnnounceTimers[statusId];
      announce();
    }, SEARCH_ANNOUNCE_DELAY_MS);
  }

  _announceStatusNow(live, text) {
    // An immediate announce (sort, bascule, Échap) cancels any pending
    // debounced one so the two paths never double-fire.
    this._cancelStatusAnnounce(live.id);
    live.textContent = text;
  }

  _renderCoherenceTable(opts) {
    const root = this.shadowRoot;
    if (!root || this._tab !== 'coherence' || this._coherence === null) {
      return;
    }
    // Typing renders the table on every keystroke (visible count
    // included) but defers the live-region announcement
    // (announceStatus, sweep) — the announce paths below stay
    // immediate for every other caller.
    const announceStatus = !(opts && opts.announceStatus === false);
    // Any reshuffle (sort, filtre, recherche, bascule) can remove the
    // anchor row: the popover closes, never floats orphaned.
    this._closeCoherencePopover();
    // Keep the view toggle in sync (mirror of the Périphériques filter).
    const viewBtn = root.querySelector('[data-coherence-view]');
    if (viewBtn) {
      viewBtn.setAttribute(
        'aria-pressed',
        String(this._coherenceView === 'to_verify')
      );
      const countSpan = viewBtn.querySelector('.count');
      if (countSpan) {
        const toVerify = (this._coherence || []).filter(coherenceToVerify).length;
        countSpan.textContent = `(${toVerify})`;
      }
    }
    const status = root.getElementById('coherence-status');
    const live = root.getElementById('coherence-status-live');
    const body = root.getElementById('coherence-body');
    if (!status || !body) {
      return;
    }

    const rows = filterCoherenceRows(this._coherence, {
      search: this._coherenceSearch,
      view: this._coherenceView,
      sort: this._coherenceSort,
    });
    // Jamais d'extension orpheline : la ligne étendue absente du
    // résultat filtré referme l'état mobile avec le reste du corps.
    if (
      this._coherenceExpandedId !== null &&
      !rows.some((r) => String(r.periph_id) === this._coherenceExpandedId)
    ) {
      this._coherenceExpandedId = null;
    }
    const statusText = coherenceStatusText(
      rows.length,
      this._coherenceSearch,
      this._coherenceView
    );
    if (rows.length === 0 && this._coherenceSearch) {
      // Explicit no-result state, announced — never a silent empty table.
      status.textContent = statusText;
      if (announceStatus && live) {
        this._announceStatusNow(live, statusText);
      }
      body.innerHTML = `
        <div class="state-message">
          Aucun périphérique ne correspond à
          “${this._escapeHtml(this._coherenceSearch)}”.
          Effacez le filtre pour restituer la table.
        </div>
      `;
      return;
    }
    if (rows.length === 0 && this._coherenceView === 'to_verify') {
      // Positive empty: nothing to check is good news, not an error.
      status.textContent = statusText;
      if (announceStatus && live) {
        this._announceStatusNow(live, statusText);
      }
      body.innerHTML = `
        <div class="state-message">
          Tout est cohérent. Aucun périphérique à vérifier.
          <br>
          <button class="row-action" type="button" data-coherence-show-all="1">
            Tout afficher
          </button>
        </div>
      `;
      return;
    }

    body.innerHTML = `
      <div class="coherence-table-wrap">
        <table class="coherence-table">
          <caption class="sr-only">Cohérence du mapping des périphériques eedomus</caption>
          ${coherenceHeadHtml(this._coherenceSort)}
          <tbody>${rows.map((row) => this._renderCoherenceRow(row)).join('')}</tbody>
        </table>
      </div>
    `;
    status.textContent = statusText;
    if (announceStatus && live) {
      this._announceStatusNow(live, statusText);
    }
  }

  // Debounced counterpart of the announce paths in _renderCoherenceTable:
  // fires once typing pauses, from the same pure message helper.
  _announceCoherenceStatus() {
    const root = this.shadowRoot;
    if (!root || this._tab !== 'coherence' || this._coherence === null) {
      return;
    }
    const live = root.getElementById('coherence-status-live');
    if (!live) {
      return;
    }
    const rows = filterCoherenceRows(this._coherence, {
      search: this._coherenceSearch,
      view: this._coherenceView,
      sort: this._coherenceSort,
    });
    live.textContent = coherenceStatusText(
      rows.length,
      this._coherenceSearch,
      this._coherenceView
    );
  }

  _coherenceSortBy(key) {
    this._coherenceSort = nextCoherenceSort(this._coherenceSort, key);
    this._renderCoherenceTable();
    // The re-render replaced the focused sort button: restore focus to
    // the control the user is operating (neutral keeps the same key).
    const focusKey = this._coherenceSort.key || key;
    const btn = this.shadowRoot.querySelector(`[data-sort-key="${focusKey}"]`);
    if (btn) {
      btn.focus();
    }
  }

  // ---- Ligne étendue mobile (ticket 2.5) ----
  // Sous 900 px, la contrepartie tactile du popover : le même
  // déclencheur, le même contenu, une surface inline dans la table.

  _toggleCoherenceExpanded(periphId) {
    // Never two detail surfaces at once: a popover opened before the
    // breakpoint crossed (narrow window + mouse) closes first.
    this._closeCoherencePopover();
    // Canonical key from the row itself — the same lookup and
    // normalization as _openCoherencePopover, so the render-side
    // predicate (String(periph_id)) always matches, hostile ids
    // included.
    const row = (this._coherence || []).find(
      (r) => String(r.periph_id) === String(periphId)
    );
    if (!row) {
      return;
    }
    const id = String(row.periph_id);
    // Focus contract (mirror of _coherenceSortBy): the re-render
    // replaces the trigger — Entrée at narrow width keeps operating
    // the same line, a tap never had the focus anyway.
    const restoreFocus =
      this.shadowRoot.activeElement === this._coherenceTriggerFor(id);
    // Une seule ligne étendue à la fois : re-tap referme, tap sur
    // une autre ligne déplace l'extension (nextCoherenceExpanded).
    this._coherenceExpandedId = nextCoherenceExpanded(
      this._coherenceExpandedId,
      id
    );
    this._renderCoherenceTable();
    if (restoreFocus) {
      const btn = this._coherenceTriggerFor(id);
      if (btn) {
        btn.focus();
      }
    }
  }

  _onCoherenceBreakpoint(ev) {
    // Wide side: the expanded row does not exist there — the popover
    // of 2.4 is the only detail surface, the state does not survive
    // the crossing (the resize listener already closed any popover).
    if (!ev.matches && this._coherenceExpandedId !== null) {
      const id = this._coherenceExpandedId;
      const root = this.shadowRoot;
      const expandedRow = root
        ? root.getElementById(coherenceExpandedRowId(id))
        : null;
      const active = root ? root.activeElement : null;
      // Focus contract: the re-render drops the expansion — the
      // user operating it (trigger or inside) lands back on the
      // trigger, like the toggle and sort paths.
      const inside = Boolean(
        (expandedRow && active && expandedRow.contains(active)) ||
          active === this._coherenceTriggerFor(id)
      );
      this._coherenceExpandedId = null;
      if (this._tab === 'coherence') {
        this._renderCoherenceTable();
      }
      if (inside) {
        const btn = this._coherenceTriggerFor(id);
        if (btn) {
          btn.focus();
        }
      }
    }
  }

  _coherenceTriggerFor(periphId) {
    const root = this.shadowRoot;
    if (!root) {
      return null;
    }
    const id = String(periphId);
    // CSS.escape guarded: when unavailable the exact dataset
    // comparison takes over — a hostile id never builds a selector.
    if (window.CSS && window.CSS.escape) {
      const btn = root.querySelector(
        `[data-coherence-popover="${window.CSS.escape(id)}"]`
      );
      if (btn) {
        return btn;
      }
    }
    const triggers = root.querySelectorAll('[data-coherence-popover]');
    for (const el of triggers) {
      if (el.dataset.coherencePopover === id) {
        return el;
      }
    }
    return null;
  }

  // ---- Navigation vers l'entité HA (ticket 2.6, CAP-8) ----
  // hass-more-info est le mécanisme standard des éléments custom HA
  // (vérifié dans le bundle frontend live) : CustomEvent composed et
  // bubbles vers le document, la boîte more-info ouvre la surface
  // standard de l'entité — web et mobile. Une navigation, pas un
  // contrôle d'édition : aucune écriture, aucun appel réseau.

  _openEntityMoreInfo(entityId) {
    if (!coherenceHasEntity(entityId)) {
      return;
    }
    const id = String(entityId);
    // Fermetures propres avant la navigation : la ligne étendue
    // mobile et le popover ne survivent pas à l'ouverture de
    // more-info — focus rendu au déclencheur, jamais de surface
    // flottante orpheline.
    if (this._coherenceExpandedId !== null) {
      const expandedId = this._coherenceExpandedId;
      const root = this.shadowRoot;
      const expandedRow = root
        ? root.getElementById(coherenceExpandedRowId(expandedId))
        : null;
      const active = root ? root.activeElement : null;
      const inside = Boolean(
        expandedRow && active && expandedRow.contains(active)
      );
      // The re-render destroys the activated link too (another row,
      // or the collapsed part of the open row): remember it to
      // restore focus to its re-rendered counterpart — the mirror
      // of the toggle/sort paths.
      const onLink = Boolean(
        !inside && active && active.closest
          ? active.closest('[data-entity-id]')
          : null
      );
      this._coherenceExpandedId = null;
      this._renderCoherenceTable();
      if (inside) {
        const btn = this._coherenceTriggerFor(expandedId);
        if (btn) {
          btn.focus();
        }
      } else if (onLink) {
        const link = this._coherenceEntityLinkFor(id);
        if (link) {
          link.focus();
        }
      }
    }
    this._closeCoherencePopover();
    this.dispatchEvent(
      new CustomEvent('hass-more-info', {
        detail: { entityId: id },
        bubbles: true,
        composed: true,
      })
    );
  }

  _coherenceEntityLinkFor(entityId) {
    const root = this.shadowRoot;
    if (!root) {
      return null;
    }
    const id = String(entityId);
    // Same guarded lookup as _coherenceTriggerFor: CSS.escape when
    // available, exact dataset comparison otherwise — a hostile id
    // never builds a selector.
    if (window.CSS && window.CSS.escape) {
      const link = root.querySelector(
        `[data-entity-id="${window.CSS.escape(id)}"]`
      );
      if (link) {
        return link;
      }
    }
    const links = root.querySelectorAll('[data-entity-id]');
    for (const el of links) {
      if (el.dataset.entityId === id) {
        return el;
      }
    }
    return null;
  }

  // ---- Popover de détail périphérique (ticket 2.4) ----
  // Desktop floating surface of the Cohérence tab. The trigger stays
  // the periph_id cell (code font); nothing else in the row opens it.

  _onCoherenceMouseOver(ev) {
    if (this._tab !== 'coherence') {
      return;
    }
    const pop = this._coherencePopover;
    const openTrigger = this._coherencePopoverTrigger;
    if (pop && openTrigger &&
        (pop.contains(ev.target) || openTrigger.contains(ev.target))) {
      // Pointer back over the trigger or the popover: the grace
      // window that closes a hover-opened popover is cancelled.
      this._cancelCoherenceLeave();
      return;
    }
    if (pop && !this._coherencePopoverByHover) {
      // Focus-opened popover: hover is ignored entirely — a sweeping
      // mouse never rips the focus out from under a keyboard user.
      return;
    }
    if (!hoverCapable()) {
      // Touch: a tap fires mouseover — only the click path opens.
      return;
    }
    if (coherenceNarrowView()) {
      // Sous 900 px (2.5), la surface est la ligne étendue : le
      // hover n'ouvre jamais le popover à côté d'elle — une seule
      // surface de détail à la fois, même fenêtre étroite + souris.
      return;
    }
    const trigger = ev.target.closest
      ? ev.target.closest('[data-coherence-popover]')
      : null;
    if (!trigger || trigger === openTrigger) {
      return;
    }
    this._cancelCoherenceHover();
    // Hover intent ~250 ms: no popover storm when sweeping the mouse
    // across the table. Keyboard opens without delay (Entrée).
    this._coherenceHoverTrigger = trigger;
    this._coherenceHoverTimer = setTimeout(() => {
      this._coherenceHoverTimer = null;
      this._coherenceHoverTrigger = null;
      this._openCoherencePopover(trigger, { focusPopover: false, byHover: true });
    }, 250);
  }

  _onCoherenceMouseOut(ev) {
    const pending = this._coherenceHoverTrigger;
    if (pending) {
      // Leaving the pending trigger before the intent delay cancels
      // the open (unless the pointer stays inside the trigger).
      const left = ev.target.closest
        ? ev.target.closest('[data-coherence-popover]')
        : null;
      if (left === pending) {
        const to = ev.relatedTarget;
        if (!to || !pending.contains(to)) {
          this._cancelCoherenceHover();
        }
      }
    }
    const pop = this._coherencePopover;
    const trigger = this._coherencePopoverTrigger;
    if (!pop || !trigger || !this._coherencePopoverByHover) {
      return;
    }
    // Hover-opened popover that never received focus: leaving the
    // trigger or the popover starts a short grace window — enough to
    // cross the 8 px gap, then the popover closes.
    const from = ev.target;
    if (!pop.contains(from) && !trigger.contains(from)) {
      return;
    }
    const to = ev.relatedTarget;
    if (to && (pop.contains(to) || trigger.contains(to))) {
      return;
    }
    this._cancelCoherenceLeave();
    this._coherenceLeaveTimer = setTimeout(() => {
      this._coherenceLeaveTimer = null;
      this._closeCoherencePopover();
    }, 200);
  }

  _cancelCoherenceHover() {
    if (this._coherenceHoverTimer) {
      clearTimeout(this._coherenceHoverTimer);
      this._coherenceHoverTimer = null;
    }
    this._coherenceHoverTrigger = null;
  }

  _cancelCoherenceLeave() {
    if (this._coherenceLeaveTimer) {
      clearTimeout(this._coherenceLeaveTimer);
      this._coherenceLeaveTimer = null;
    }
  }

  _openCoherencePopover(trigger, opts) {
    const periphId = trigger.dataset.coherencePopover;
    const row = (this._coherence || []).find(
      (r) => String(r.periph_id) === String(periphId)
    );
    if (!row) {
      return;
    }
    // One floating surface at a time: opening another closes the first.
    this._closeCoherencePopover();
    const pop = document.createElement('div');
    pop.className = 'periph-popover';
    pop.setAttribute('role', 'dialog');
    pop.setAttribute(
      'aria-label',
      `Détail du périphérique ${row.name || row.periph_id} (${row.periph_id})`
    );
    pop.innerHTML = coherenceDetailHtml(row);
    this.shadowRoot.appendChild(pop);
    this._coherencePopover = pop;
    this._coherencePopoverTrigger = trigger;
    this._coherencePopoverByHover = Boolean(opts && opts.byHover);
    trigger.setAttribute('aria-expanded', 'true');
    // haspopup lives on the open popover only: the static template
    // stays surface-neutral (the narrow side expands a row, 2.5).
    trigger.setAttribute('aria-haspopup', 'dialog');
    this._positionCoherencePopover(pop, trigger);
    this._wireCoherencePopover(pop, trigger);
    if (opts && opts.focusPopover) {
      const focusables = this._popoverFocusables(pop);
      if (focusables.length > 0) {
        focusables[0].focus();
      }
    }
  }

  _closeCoherencePopover() {
    this._cancelCoherenceHover();
    this._cancelCoherenceLeave();
    const pop = this._coherencePopover;
    const trigger = this._coherencePopoverTrigger;
    this._coherencePopover = null;
    this._coherencePopoverTrigger = null;
    this._coherencePopoverByHover = false;
    if (this._coherenceDismiss) {
      document.removeEventListener('click', this._coherenceDismiss, true);
      document.removeEventListener('scroll', this._coherenceDismiss, true);
      window.removeEventListener('resize', this._coherenceDismiss);
      window.removeEventListener('orientationchange', this._coherenceDismiss);
      this._coherenceDismiss = null;
    }
    if (this._coherenceFocusOut) {
      this.shadowRoot.removeEventListener('focusout', this._coherenceFocusOut);
      this._coherenceFocusOut = null;
    }
    if (trigger) {
      trigger.setAttribute('aria-expanded', 'false');
      trigger.removeAttribute('aria-haspopup');
    }
    if (!pop) {
      return;
    }
    // Focus goes back to the trigger only when it was inside the
    // popover — a mouse user focused elsewhere keeps it there.
    const active = this.shadowRoot.activeElement;
    const focusInside = active != null && pop.contains(active);
    pop.remove();
    if (focusInside && trigger && trigger.isConnected) {
      trigger.focus();
    }
  }

  _wireCoherencePopover(pop, trigger) {
    // Outside click and any scroll that can detach the anchor row close
    // the popover — a single listener pair, active only while open.
    this._coherenceDismiss = (ev) => {
      const path = ev.composedPath ? ev.composedPath() : [ev.target];
      if (path.indexOf(pop) !== -1) {
        return;
      }
      if (ev.type === 'click' && path.indexOf(trigger) !== -1) {
        return;
      }
      this._closeCoherencePopover();
    };
    document.addEventListener('click', this._coherenceDismiss, true);
    document.addEventListener('scroll', this._coherenceDismiss, true);
    // A resize or an orientation change invalidates the fixed
    // coordinates: close instead of floating at a stale position.
    window.addEventListener('resize', this._coherenceDismiss);
    window.addEventListener('orientationchange', this._coherenceDismiss);
    // A hover-opened popover that never held focus closes as soon as
    // the focus lands outside the trigger and the popover (ex. Tab
    // depuis le déclencheur).
    this._coherenceFocusOut = (ev) => {
      if (!this._coherencePopoverByHover) {
        return;
      }
      const to = ev.relatedTarget;
      if (to && (pop.contains(to) || trigger.contains(to))) {
        return;
      }
      this._closeCoherencePopover();
    };
    this.shadowRoot.addEventListener('focusout', this._coherenceFocusOut);
    // Focus entering the popover hands it over to the keyboard
    // contract: the hover-close grace stops applying.
    pop.addEventListener('focusin', () => {
      this._coherencePopoverByHover = false;
    });
    // Keyboard contract: Tab loops inside the popover (focus trap),
    // Échap closes and returns the focus to the trigger.
    pop.addEventListener('keydown', (ev) => {
      if (ev.key === 'Escape') {
        ev.preventDefault();
        ev.stopPropagation();
        this._closeCoherencePopover();
        return;
      }
      if (ev.key !== 'Tab') {
        return;
      }
      const focusables = this._popoverFocusables(pop);
      if (focusables.length === 0) {
        ev.preventDefault();
        return;
      }
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const idx = focusables.indexOf(this.shadowRoot.activeElement);
      if (ev.shiftKey && idx <= 0) {
        ev.preventDefault();
        last.focus();
      } else if (!ev.shiftKey && (idx === -1 || idx === focusables.length - 1)) {
        ev.preventDefault();
        first.focus();
      }
    });
  }

  _positionCoherencePopover(pop, trigger) {
    const anchor = trigger.getBoundingClientRect();
    const rect = pop.getBoundingClientRect();
    const pos = coherencePopoverPosition(
      { left: anchor.left, top: anchor.top, bottom: anchor.bottom },
      { width: rect.width, height: rect.height },
      { width: window.innerWidth, height: window.innerHeight }
    );
    pop.style.left = `${pos.left}px`;
    pop.style.top = `${pos.top}px`;
  }

  _popoverFocusables(pop) {
    return Array.from(
      pop.querySelectorAll(POPOVER_FOCUSABLE_SELECTOR)
    );
  }

  _renderCoherenceSkeleton() {
    // Skeletons shaped like the expected content: table header + rows.
    // The head is the SAME generator as the loaded table (sweep) —
    // shared labels and markup, neutral sort. inert keeps the loading
    // copy out of the tab order: its buttons are placeholders, not
    // controls, and the table is aria-hidden anyway.
    const row = `
      <tr><td colspan="${COHERENCE_COLUMNS.length}"><div class="skeleton-cell" aria-hidden="true"></div></td></tr>`;
    return `
      <div class="coherence-table-wrap" role="status" aria-label="Chargement de la cohérence…">
        <table class="coherence-table" aria-hidden="true" inert>
          ${coherenceHeadHtml({ key: null, dir: null })}
          <tbody>${row.repeat(8)}</tbody>
        </table>
      </div>
    `;
  }

  _renderCoherenceRow(row) {
    // Thin shell over the pure composition (2.6): the class only
    // supplies the volatile state the helpers cannot reach.
    return coherenceRowHtml(
      row,
      this._coherenceExpandedId,
      coherenceNarrowView()
    );
  }

  _renderPeriphToolbar() {
    const touchedCount = (this._periphs || []).filter((row) => row.modified).length;
    return `
      <div class="toolbar">
        <div class="search">
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M15.5 14h-.79l-.28-.27a6.5 6.5 0 1 0-.7.7l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0A4.5 4.5 0 1 1 14 9.5 4.5 4.5 0 0 1 9.5 14z"/></svg>
          <input id="periph-search" type="search"
                 placeholder="Rechercher par nom ou usage_id"
                 aria-label="Rechercher un périphérique par nom ou usage_id"
                 value="${this._escapeHtml(this._search)}">
        </div>
        <button class="filter-touches" type="button"
                aria-pressed="${this._touchedOnly}">
          Périphériques touchés <span class="count">(${touchedCount})</span>
        </button>
      </div>
      <p class="result-count" id="periph-status"></p>
      <p class="sr-only" id="periph-status-live" role="status"></p>
      <div class="periph-list" id="periph-list"></div>
    `;
  }

  _renderPeriphList(opts) {
    const root = this.shadowRoot;
    if (!root || this._tab !== 'peripheriques') {
      return;
    }
    // Typing re-renders the list on every keystroke (visible count
    // included) but defers the live-region announcement (announceStatus,
    // sweep); every other caller keeps the immediate announce.
    const announceStatus = !(opts && opts.announceStatus === false);
    const filterBtn = root.querySelector('.filter-touches');
    if (filterBtn) {
      filterBtn.setAttribute('aria-pressed', String(this._touchedOnly));
      const countSpan = filterBtn.querySelector('.count');
      if (countSpan) {
        const touched = (this._periphs || []).filter((row) => row.modified).length;
        countSpan.textContent = `(${touched})`;
      }
    }

    const list = root.getElementById('periph-list');
    const status = root.getElementById('periph-status');
    const live = root.getElementById('periph-status-live');
    if (!list || !status) {
      return;
    }

    if (this._error) {
      // The error state owns the status line (blank) — any pending
      // debounced announce dies with it.
      this._cancelStatusAnnounce('periph-status-live');
      status.textContent = '';
      if (live) {
        live.textContent = '';
      }
      list.innerHTML = `
        <div class="state-message" role="alert">
          Impossible de charger les périphériques : ${this._escapeHtml(this._error)}.
          <br>
          <button class="retry" type="button">Réessayer</button>
        </div>
      `;
      return;
    }

    if (this._periphs === null) {
      this._cancelStatusAnnounce('periph-status-live');
      status.textContent = '';
      if (live) {
        live.textContent = '';
      }
      list.innerHTML = '<div class="skeleton-row"></div>'.repeat(6);
      return;
    }

    if (this._periphs.length === 0) {
      this._cancelStatusAnnounce('periph-status-live');
      status.textContent = '';
      if (live) {
        live.textContent = '';
      }
      list.innerHTML = `
        <div class="state-message">
          Aucun périphérique détecté. Vérifiez que l'intégration eedomus est
          configurée.
        </div>
      `;
      return;
    }

    const rows = this._filteredPeriphs();
    const parts = [];
    for (const row of rows) {
      parts.push(this._renderRow(row));
    }
    list.innerHTML = parts.join('');

    status.textContent = periphStatusText(
      this._periphs.length,
      rows.length,
      this._touchedOnly
    );
    if (announceStatus && live) {
      this._announceStatusNow(
        live,
        periphStatusText(this._periphs.length, rows.length, this._touchedOnly)
      );
    }
  }

  // Debounced counterpart of the announce path in _renderPeriphList:
  // fires once typing pauses, from the same pure message helper.
  _announcePeriphStatus() {
    const root = this.shadowRoot;
    if (!root || this._tab !== 'peripheriques') {
      return;
    }
    // The empty and error states deliberately keep their status line
    // blank — never overwrite it with a count (their own messages
    // carry the state).
    if (
      this._periphs === null ||
      this._periphs.length === 0 ||
      this._error
    ) {
      return;
    }
    const live = root.getElementById('periph-status-live');
    if (!live) {
      return;
    }
    const rows = this._filteredPeriphs();
    live.textContent = periphStatusText(
      this._periphs.length,
      rows.length,
      this._touchedOnly
    );
  }

  _renderRow(row) {
    const badge = row.modified
      ? `
        <span class="badge-modified"
              title="Modifié par ${this._escapeAttr(row.modified_by_rule)}, ${this._escapeAttr(row.modified_date || 'date inconnue')}"
              aria-label="Modifié par la règle « ${this._escapeAttr(row.modified_by_rule)} », ${this._escapeAttr(row.modified_date || 'date inconnue')}">
          <span class="dot" aria-hidden="true"></span>
          <svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true"><path fill="currentColor" d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
          modifié
        </span>`
      : '<span></span>';

    const mappingMeta = [row.device_class, row.unit].filter(Boolean).join(' · ');
    return `
      <div class="periph-row">
        <div class="row-top">
          <div class="periph-identity">
            <span class="periph-name">${this._escapeHtml(row.name || row.periph_id)}</span>
            <span class="periph-meta">usage_id <code>${this._escapeHtml(row.usage_id || '?')}</code></span>
          </div>
          ${badge}
        </div>
        <div class="periph-mapping">
          <span class="ha-entity">${row.entity_id ? this._escapeHtml(row.entity_id) : '<em>aucune entité</em>'}</span>
          <span class="mapping-meta">${this._escapeHtml(mappingMeta || row.platform || '')}</span>
        </div>
        <button class="row-action" type="button"
                data-periph-id="${this._escapeAttr(row.periph_id)}"
                data-usage-id="${this._escapeAttr(row.usage_id || '')}">
          Créer une règle pour ce périphérique
        </button>
      </div>
    `;
  }

  _escapeHtml(value) {
    return escapeHtml(value);
  }

  _escapeAttr(value) {
    return this._escapeHtml(value);
  }

  // ================= Règles (P.1.4) =================

  async _loadMapping() {
    if (!this._hass) {
      return;
    }
    this._mappingError = null;
    try {
      const result = await this._hass.callWS({
        type: 'eedomus/get_mapping',
      });
      this._mapping = (result && result.mapping) || {};
    } catch (err) {
      this._mappingError = (err && (err.message || err.code)) || 'commande refusée';
    }
    if (this._tab === 'regles') {
      const content = this.shadowRoot.getElementById('tab-content');
      if (content) {
        content.innerHTML = this._renderRulesTab();
        this._wireRulesTab();
      }
    }
  }

  _usageIdRules() {
    const mappings = (this._mapping && this._mapping.custom_usage_id_mappings) || {};
    return Object.entries(mappings)
      .map(([usageId, rule]) => ({ usageId, rule }))
      .sort((a, b) => a.usageId.localeCompare(b.usageId, undefined, { numeric: true }));
  }

  _openRuleForm(usageId) {
    this._saveState = null;
    this._confirmDelete = null;
    this._ruleForm = {
      usage_id: usageId || '',
      justification: '',
      ha_entity: 'sensor',
      ha_subtype: '',
    };
    this._validation = { valid: false, message: '' };
    this._scheduleValidation();
    const content = this.shadowRoot.getElementById('tab-content');
    if (content) {
      content.innerHTML = this._renderRulesTab();
      this._wireRulesTab();
      const input = this.shadowRoot.getElementById('rule-usage-id');
      if (input) {
        input.focus();
      }
    }
  }

  _scheduleValidation() {
    if (this._validateTimer) {
      clearTimeout(this._validateTimer);
    }
    this._validateTimer = setTimeout(() => this._validateRuleForm(), 350);
  }

  async _validateRuleForm() {
    const form = this._ruleForm;
    if (!form || !this._hass) {
      return;
    }
    const fragment = {
      custom_usage_id_mappings: {
        [form.usage_id]: {
          ha_entity: form.ha_entity,
          ha_subtype: form.ha_subtype,
          justification: form.justification,
        },
      },
    };
    try {
      const result = await this._hass.callWS({
        type: 'eedomus/validate_config',
        yaml_content: this._yamlDump(fragment),
      });
      if (result && result.valid) {
        this._validation = { valid: true, message: '' };
      } else {
        const error = result && result.error;
        this._validation = {
          valid: false,
          message: (error && (error.message || error.error)) || 'configuration invalide',
        };
      }
    } catch (err) {
      this._validation = {
        valid: false,
        message: (err && (err.message || err.code)) || 'validation impossible',
      };
    }
    if (this._tab === 'regles' && this._ruleForm) {
      this._updateRuleFormState();
    }
  }

  _updateRuleFormState() {
    const form = this._ruleForm;
    if (!form) {
      return;
    }
    const saveBtn = this.shadowRoot.getElementById('rule-save');
    const validationEl = this.shadowRoot.getElementById('rule-validation');
    const usageInput = this.shadowRoot.getElementById('rule-usage-id');
    if (usageInput) {
      usageInput.setAttribute('aria-invalid', String(!form.usage_id));
    }
    if (validationEl) {
      validationEl.textContent = this._validation.valid
        ? ''
        : this._validation.message;
    }
    if (saveBtn) {
      const clientValid = form.usage_id && form.justification.trim() !== '';
      saveBtn.disabled = !(clientValid && this._validation.valid) ||
        this._saveState === 'saving' ||
        this._saveState === 'applying';
      saveBtn.textContent =
        this._saveState === 'saving'
          ? 'Sauvegarde…'
          : this._saveState === 'applying'
            ? 'Application…'
            : 'Enregistrer';
    }
    this._updateRulesStatus();
  }

  _updateRulesStatus() {
    const status = this.shadowRoot.getElementById('rules-status');
    if (!status) {
      return;
    }
    if (this._saveState === 'saving') {
      status.textContent = 'Sauvegarde…';
    } else if (this._saveState === 'applying') {
      status.textContent = 'Application…';
    } else if (this._saveState && this._saveState.applied === true) {
      status.textContent = 'Configuration appliquée.';
    } else if (this._saveState && this._saveState.applied) {
      const applied = this._saveState.applied;
      status.textContent = `Règle appliquée. ${applied.entity_id} est maintenant en ${applied.unit}.`;
    } else if (this._saveState && this._saveState.error) {
      status.textContent = `Échec de la sauvegarde : ${this._saveState.error}. Le formulaire conserve vos modifications.`;
    } else if (this._validation.message) {
      status.textContent = this._validation.message;
    } else {
      status.textContent = this._rulesStatus;
    }
  }

  async _persistMapping(mapping) {
    // Shared save path: persist through eedomus/save_mapping, then the
    // reloaded peripherals power the nominative feedback.
    this._saveState = 'saving';
    this._updateYamlState();
    this._updateRuleFormState();
    try {
      await this._hass.callWS({
        type: 'eedomus/save_mapping',
        mapping,
      });
      this._saveState = 'applying';
      this._mapping = mapping;
      this._updateYamlState();
      this._updateRuleFormState();
      await this._loadPeripherals();
      this._saveState = { applied: true };
      return true;
    } catch (err) {
      this._saveState = {
        error: (err && (err.message || err.code)) || 'erreur inconnue',
      };
      return false;
    }
  }

  async _saveRules() {
    const form = this._ruleForm;
    if (!form || !this._mapping) {
      return;
    }
    const mapping = JSON.parse(JSON.stringify(this._mapping));
    mapping.custom_usage_id_mappings = mapping.custom_usage_id_mappings || {};
    mapping.custom_usage_id_mappings[form.usage_id] = {
      ha_entity: form.ha_entity,
      ha_subtype: form.ha_subtype,
      justification: form.justification,
    };
    mapping.metadata = mapping.metadata || {};
    mapping.metadata.last_modified = new Date().toISOString().slice(0, 16).replace('T', ' ');
    const ok = await this._persistMapping(mapping);
    if (ok) {
      const rule = form.usage_id;
      const row = (this._periphs || []).find((p) => p.usage_id === rule);
      this._saveState = {
        applied: {
          entity_id: row && row.entity_id ? row.entity_id : `usage_id ${rule}`,
          unit: row && row.unit ? row.unit : 'sa nouvelle valeur',
        },
      };
      this._ruleForm = null;
    }
    const content = this.shadowRoot.getElementById('tab-content');
    if (content && this._tab === 'regles') {
      content.innerHTML = this._renderRulesTab();
      this._wireRulesTab();
    }
    this._updateRulesStatus();
  }

  async _deleteRule(usageId) {
    if (!this._mapping) {
      return;
    }
    if (this._confirmDelete !== usageId) {
      // Two-gesture delete: first click asks for confirmation.
      this._confirmDelete = usageId;
      this._renderRulesList();
      return;
    }
    this._confirmDelete = null;
    const mapping = JSON.parse(JSON.stringify(this._mapping));
    if (mapping.custom_usage_id_mappings) {
      delete mapping.custom_usage_id_mappings[usageId];
    }
    this._saveState = 'saving';
    try {
      await this._hass.callWS({ type: 'eedomus/save_mapping', mapping });
      this._mapping = mapping;
      this._saveState = { applied: { entity_id: `règle ${usageId}`, unit: 'supprimée' } };
      await this._loadPeripherals();
    } catch (err) {
      this._saveState = {
        error: (err && (err.message || err.code)) || 'erreur inconnue',
      };
    }
    const content = this.shadowRoot.getElementById('tab-content');
    if (content && this._tab === 'regles') {
      content.innerHTML = this._renderRulesTab();
      this._wireRulesTab();
    }
    this._updateRulesStatus();
  }

  _renderRulesList() {
    const listEl = this.shadowRoot.getElementById('rules-list');
    if (!listEl) {
      return;
    }
    const rules = this._usageIdRules();
    if (rules.length === 0) {
      listEl.innerHTML = `
        <div class="state-message">
          Aucune règle de mapping. Le mapping par défaut s'applique.
        </div>
      `;
      return;
    }
    listEl.innerHTML = rules
      .map(({ usageId, rule }) => {
        const confirm = this._confirmDelete === usageId;
        return `
        <div class="periph-row">
          <div class="row-top">
            <div class="periph-identity">
              <span class="periph-name">usage_id <code>${this._escapeHtml(usageId)}</code></span>
              <span class="periph-meta">${this._escapeHtml(rule.justification || '')}</span>
            </div>
          </div>
          <div class="periph-mapping">
            <span class="ha-entity">${this._escapeHtml(rule.ha_entity || '')}${rule.ha_subtype ? '.' + this._escapeHtml(rule.ha_subtype) : ''}</span>
          </div>
          <button class="row-action" type="button" data-edit-rule="${this._escapeAttr(usageId)}">
            Modifier
          </button>
          <button class="row-action" type="button" data-delete-rule="${this._escapeAttr(usageId)}">
            ${confirm ? 'Confirmer la suppression ?' : 'Supprimer'}
          </button>
        </div>
      `;
      })
      .join('');
  }

  _renderRulesTab() {
    if (this._mappingError) {
      return `
        <div class="state-message" role="alert">
          Impossible de charger la configuration : ${this._escapeHtml(this._mappingError)}.
          <br>
          <button class="retry" type="button" data-retry="mapping">Réessayer</button>
        </div>
      `;
    }
    if (this._mapping === null) {
      return '<div class="skeleton-row"></div>'.repeat(4);
    }

    const rulesListHtml = `
      <p class="result-count" id="rules-status" role="status"></p>
      <div class="periph-list" id="rules-list"></div>
    `;

    const modeToggle = `
      <div class="mode-toggle" role="group" aria-label="Mode d'édition des règles">
        <button type="button" data-rule-mode="form" aria-pressed="${this._rulesMode === 'form'}">Formulaire</button>
        <button type="button" data-rule-mode="yaml" aria-pressed="${this._rulesMode === 'yaml'}">YAML</button>
      </div>
    `;

    if (this._rulesMode === 'yaml') {
      const errorHtml = this._yamlError
        ? `<p class="form-validation" role="alert">${this._escapeHtml(this._yamlError.message)}</p>`
        : '';
      return `
        ${modeToggle}
        <div class="yaml-editor-wrap">
          <div class="yaml-gutter" id="yaml-gutter" aria-hidden="true"></div>
          <div class="yaml-code-area">
            <pre class="yaml-highlight" id="yaml-highlight" aria-hidden="true"></pre>
            <textarea class="yaml-editor" id="yaml-editor" spellcheck="false"
              aria-label="Éditeur YAML du mapping custom"
              aria-describedby="yaml-error"></textarea>
          </div>
        </div>
        <p class="form-validation" id="yaml-error" role="alert">${errorHtml ? this._escapeHtml(this._yamlError.message) : ''}</p>
        <div class="form-actions">
          <button class="row-action" id="yaml-save" type="button" disabled>Enregistrer</button>
        </div>
        <p class="result-count" id="rules-status" role="status"></p>
      `;
    }

    if (!this._ruleForm) {
      const prefillNote = this._pendingRuleUsageId
        ? `<p class="result-count">usage_id pré-rempli : <code>${this._escapeHtml(this._pendingRuleUsageId)}</code></p>`
        : '';
      return `
        ${modeToggle}
        ${prefillNote}
        <div class="toolbar">
          <button class="row-action" type="button" data-new-rule="${this._escapeAttr(this._pendingRuleUsageId || '')}">
            Créer une règle
          </button>
        </div>
        ${rulesListHtml}
      `;
    }

    const form = this._ruleForm;
    const datalistId = 'rule-usage-id-options';
    const options = (this._periphs || [])
      .map((p) => ({ usage: p.usage_id, name: p.name }))
      .filter((p) => p.usage)
      .sort((a, b) => a.name.localeCompare(b.name))
      .map(
        (p) =>
          `<option value="${this._escapeAttr(p.usage)}">${this._escapeHtml(p.name)}</option>`
      )
      .join('');

    return `
      <form class="rule-form" id="rule-form" novalidate>
        <div class="form-field">
          <label for="rule-usage-id">usage_id</label>
          <input id="rule-usage-id" list="${datalistId}" type="text" inputmode="numeric"
                 placeholder="ex. 7" required
                 aria-describedby="rule-validation"
                 value="${this._escapeAttr(form.usage_id)}">
          <datalist id="${datalistId}">${options}</datalist>
        </div>
        <div class="form-field">
          <label for="rule-name">Nom de la règle</label>
          <input id="rule-name" type="text" placeholder="ex. Unité température salon"
                 required aria-describedby="rule-validation"
                 value="${this._escapeAttr(form.justification)}">
        </div>
        <div class="form-field">
          <label for="rule-entity">Plateforme HA</label>
          <select id="rule-entity">
            ${['sensor', 'light', 'switch', 'cover', 'climate', 'binary_sensor', 'select', 'text_sensor']
              .map(
                (platform) =>
                  `<option value="${platform}"${form.ha_entity === platform ? ' selected' : ''}>${platform}</option>`
              )
              .join('')}
          </select>
        </div>
        <div class="form-field">
          <label for="rule-subtype">Classe de périphérique</label>
          <select id="rule-subtype">
            <option value=""${form.ha_subtype === '' ? ' selected' : ''}>(aucune)</option>
            ${['temperature', 'humidity', 'energy', 'power', 'time', 'cpu', 'disk_free_space', 'text']
              .map(
                (subtype) =>
                  `<option value="${subtype}"${form.ha_subtype === subtype ? ' selected' : ''}>${subtype}</option>`
              )
              .join('')}
          </select>
          <span class="form-hint">La classe détermine device_class et unité appliquées (ex. temperature → °C).</span>
        </div>
        <p id="rule-validation" class="form-validation" role="alert"></p>
        <div class="form-actions">
          <button class="row-action" type="button" data-cancel-rule="1">Annuler</button>
          <button class="row-action rule-save" id="rule-save" type="button" disabled>Enregistrer</button>
        </div>
      </form>
      ${rulesListHtml}
    `;
  }

  _wireRulesTab() {
    const content = this.shadowRoot.getElementById('tab-content');
    if (!content) {
      return;
    }
    if (this._rulesMode === 'yaml') {
      const editor = this.shadowRoot.getElementById('yaml-editor');
      if (editor) {
        if (this._yamlText === null) {
          this._yamlText = this._yamlDumpFull(this._mapping || {});
        }
        if (editor.value !== this._yamlText) {
          editor.value = this._yamlText;
        }
        this._renderYamlHighlight();
        this._updateYamlState();
        editor.addEventListener('scroll', () => this._syncYamlScroll());
        editor.addEventListener('keydown', (ev) => {
          // Tab inserts spaces in the editor instead of leaving it
          if (ev.key === 'Tab') {
            ev.preventDefault();
            const start = editor.selectionStart;
            const end = editor.selectionEnd;
            editor.value = editor.value.slice(0, start) + '  ' + editor.value.slice(end);
            editor.selectionStart = editor.selectionEnd = start + 2;
            editor.dispatchEvent(new Event('input', { bubbles: true }));
          }
        });
        if (this._yamlFocusPending) {
          this._yamlFocusPending = false;
          editor.focus();
        }
      }
      this._updateRulesStatus();
      return;
    }
    this._renderRulesList();
    if (this._ruleForm) {
      this._updateRuleFormState();
      const usageInput = this.shadowRoot.getElementById('rule-usage-id');
      if (usageInput && usageInput.value !== this._ruleForm.usage_id) {
        usageInput.value = this._ruleForm.usage_id;
      }
    } else {
      this._updateRulesStatus();
    }
  }

  _setRulesMode(mode) {
    if (mode === this._rulesMode) {
      return;
    }
    if (mode === 'yaml') {
      // form -> yaml: the YAML reflects the current mapping state
      this._yamlText = this._yamlDumpFull(this._mapping || {});
      this._yamlError = null;
      this._yamlValidated = null;
      this._yamlFocusPending = true;
      this._rulesMode = 'yaml';
      const content = this.shadowRoot.getElementById('tab-content');
      content.innerHTML = this._renderRulesTab();
      this._wireRulesTab();
      this._scheduleYamlValidation();
      this._announceMode('YAML');
    } else {
      // yaml -> form: allowed only when the text validates - never lose
      // content silently. The validated config becomes the mapping.
      if (!this._yamlValidated) {
        this._announceMode(
          'Formulaire',
          this._yamlError && this._yamlError.message
            ? `bascule refusée : ${this._yamlError.message}`
            : 'bascule refusée : corrigez les erreurs YAML ou revenez au texte validé'
        );
        return;
      }
      this._mapping = this._yamlValidated;
      this._ruleForm = null;
      this._rulesMode = 'form';
      const content = this.shadowRoot.getElementById('tab-content');
      content.innerHTML = this._renderRulesTab();
      this._wireRulesTab();
      this._announceMode('Formulaire');
    }
  }

  _announceMode(mode, extra = '') {
    const status = this.shadowRoot.getElementById('rules-status');
    if (status) {
      status.textContent = `Mode ${mode}${extra ? ` — ${extra}` : ''}.`;
    }
  }

  _scheduleYamlValidation() {
    if (this._yamlTimer) {
      clearTimeout(this._yamlTimer);
    }
    this._yamlTimer = setTimeout(() => this._validateYaml(), 400);
  }

  async _validateYaml() {
    const editor = this.shadowRoot.getElementById('yaml-editor');
    if (!editor || !this._hass || this._rulesMode !== 'yaml') {
      return;
    }
    const text = editor.value;
    try {
      const result = await this._hass.callWS({
        type: 'eedomus/validate_config',
        yaml_content: text,
      });
      if (result && result.valid) {
        this._yamlError = null;
        this._yamlValidated = (result.validated_config || null);
      } else {
        const raw = (result && result.error) || {};
        const message =
          (typeof raw === 'string' ? raw : raw.error || raw.message) ||
          'configuration invalide';
        this._yamlError = { message, line: this._yamlLineFromError(message, text) };
        this._yamlValidated = null;
      }
    } catch (err) {
      // Syntax errors arrive as websocket errors carrying "line N"
      const message = (err && (err.message || err.code)) || 'validation impossible';
      this._yamlError = {
        message,
        line: this._yamlLineFromError(message, editor.value),
      };
      this._yamlValidated = null;
    }
    if (editor.value === text) {
      this._updateYamlState();
      this._updateRulesStatus();
    }
  }

  _yamlLineFromError(message, text) {
    // PyYAML syntax errors carry "line N"; schema errors carry a path
    // whose last key can be located in the text.
    const m = /line (\d+)/.exec(message);
    if (m) {
      return parseInt(m[1], 10);
    }
    const keyMatch = /at '([^']+)'/m.exec(message);
    if (keyMatch) {
      const parts = keyMatch[1].split('.');
      const last = parts[parts.length - 1].replace(/\[.*?\]/g, '');
      if (last) {
        const lines = text.split('\n');
        for (let i = 0; i < lines.length; i++) {
          if (lines[i].includes(last)) {
            return i + 1;
          }
        }
      }
    }
    return null;
  }

  _updateYamlState() {
    const errEl = this.shadowRoot.getElementById('yaml-error');
    const saveBtn = this.shadowRoot.getElementById('yaml-save');
    if (errEl) {
      errEl.textContent = this._yamlError
        ? `ligne ${this._yamlError.line || '?'} : ${this._yamlError.message}`
        : '';
    }
    if (saveBtn) {
      saveBtn.disabled = !this._yamlValidated ||
        this._saveState === 'saving' ||
        this._saveState === 'applying';
      saveBtn.textContent =
        this._saveState === 'saving'
          ? 'Sauvegarde…'
          : this._saveState === 'applying'
            ? 'Application…'
            : 'Enregistrer';
    }
  }

  async _saveYamlMapping() {
    if (!this._yamlValidated) {
      return;
    }
    await this._persistMapping(this._yamlValidated);
    if (this._saveState && this._saveState.applied) {
      // The saved mapping becomes the new YAML baseline
      this._yamlText = this._yamlDumpFull(this._mapping || {});
      const editor = this.shadowRoot.getElementById('yaml-editor');
      if (editor) {
        editor.value = this._yamlText;
        this._renderYamlHighlight();
      }
    }
    this._updateYamlState();
    this._updateRulesStatus();
  }

  _renderYamlHighlight() {
    const editor = this.shadowRoot.getElementById('yaml-editor');
    const pre = this.shadowRoot.getElementById('yaml-highlight');
    const gutter = this.shadowRoot.getElementById('yaml-gutter');
    if (!editor || !pre || !gutter) {
      return;
    }
    const lines = editor.value.split('\n');
    gutter.textContent = lines.map((_, i) => i + 1).join('\n') + '\n';
    pre.innerHTML = lines.map((line) => this._highlightYamlLine(line)).join('\n');
    this._syncYamlScroll();
  }

  _highlightYamlLine(line) {
    // Full-line comment
    if (/^\s*#/.test(line)) {
      return `<span class="tok-comment">${this._escapeHtml(line)}</span>`;
    }
    // Trailing comment (heuristic: whitespace before #)
    let code = line;
    let comment = '';
    const commentIdx = line.search(/\s#/);
    if (commentIdx !== -1) {
      code = line.slice(0, commentIdx + 1);
      comment = `<span class="tok-comment">${this._escapeHtml(line.slice(commentIdx + 1))}</span>`;
    }
    // Key up to the first colon, highlighted value after it
    const colonIdx = code.indexOf(':');
    let html;
    if (colonIdx === -1) {
      html = this._highlightYamlValue(code);
    } else {
      const key = code.slice(0, colonIdx);
      const value = code.slice(colonIdx + 1);
      html = `<span class="tok-key">${this._escapeHtml(key)}</span>:`
        + this._highlightYamlValue(value);
    }
    return html + comment;
  }

  _highlightYamlValue(text) {
    // Quoted strings are parked as placeholders first so the number and
    // boolean rules never recolor their content.
    let out = this._escapeHtml(text);
    const strings = [];
    out = out.replace(/&quot;[\s\S]*?&quot;|&#39;[\s\S]*?&#39;/g, (m) => {
      strings.push(`<span class="tok-str">${m}</span>`);
      return `\u0000${strings.length - 1}\u0000`;
    });
    out = out
      .replace(/\b(true|false|null)\b/g,
        '<span class="tok-bool">$1</span>')
      .replace(/(^|\s)(-?\d+(?:\.\d+)?)(?=\s|$)/gm,
        (m, prefix, num) => `${prefix}<span class="tok-num">${num}</span>`);
    return out.replace(/\u0000(\d+)\u0000/g, (m, i) => strings[i]);
  }

  _syncYamlScroll() {
    const editor = this.shadowRoot.getElementById('yaml-editor');
    const pre = this.shadowRoot.getElementById('yaml-highlight');
    const gutter = this.shadowRoot.getElementById('yaml-gutter');
    if (!editor || !pre || !gutter) {
      return;
    }
    pre.scrollTop = editor.scrollTop;
    pre.scrollLeft = editor.scrollLeft;
    gutter.scrollTop = editor.scrollTop;
  }

  _yamlDumpFull(obj, indent = 0) {
    /** Serialize the full custom mapping grammar to YAML: nested dicts,
     * lists, scalars. Strings are quoted unless they are plain words -
     * JSON string escaping is valid YAML double-quoted scalar syntax. */
    const pad = ' '.repeat(indent);
    const scalar = (value) => {
      if (value === null || value === undefined) {
        return 'null';
      }
      if (typeof value === 'boolean') {
        return value ? 'true' : 'false';
      }
      if (typeof value === 'number') {
        return String(value);
      }
      const str = String(value);
      if (/^[A-Za-z_][A-Za-z0-9_\-]*$/.test(str)) {
        return str;
      }
      return JSON.stringify(str);
    };
    const lines = [];
    for (const [key, value] of Object.entries(obj)) {
      if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
        const entries = Object.entries(value);
        if (entries.length === 0) {
          lines.push(`${pad}${scalar(key)}: {}`);
        } else {
          lines.push(`${pad}${scalar(key)}:`);
          lines.push(this._yamlDumpFull(value, indent + 2));
        }
      } else if (Array.isArray(value)) {
        if (value.length === 0) {
          lines.push(`${pad}${scalar(key)}: []`);
        } else {
          lines.push(`${pad}${scalar(key)}:`);
          for (const item of value) {
            if (item !== null && typeof item === 'object') {
              // list item as inline mapping, nested keys at indent + 4
              const itemLines = this._yamlDumpFull(item, indent + 4);
              lines.push(itemLines.replace(
                new RegExp(`^${' '.repeat(indent + 4)}`),
                `${' '.repeat(indent + 2)}- `
              ));
            } else {
              lines.push(`${pad}- ${scalar(item)}`);
            }
          }
        }
      } else {
        lines.push(`${pad}${scalar(key)}: ${scalar(value)}`);
      }
    }
    return lines.join('\n') + (indent === 0 ? '\n' : '');
  }

  _onRulesEvent(ev) {
    const modeBtn = ev.target.closest('[data-rule-mode]');
    if (modeBtn) {
      this._setRulesMode(modeBtn.dataset.ruleMode);
      return;
    }
    if (ev.target.id === 'yaml-save') {
      this._saveYamlMapping();
      return;
    }
    const newRule = ev.target.closest('[data-new-rule]');
    if (newRule) {
      this._openRuleForm(newRule.dataset.newRule || this._pendingRuleUsageId || '');
      this._pendingRuleUsageId = null;
      return;
    }
    const editRule = ev.target.closest('[data-edit-rule]');
    if (editRule) {
      const usageId = editRule.dataset.editRule;
      const entry =
        (this._mapping.custom_usage_id_mappings || {})[usageId] || {};
      this._ruleForm = {
        usage_id: usageId,
        justification: entry.justification || '',
        ha_entity: entry.ha_entity || 'sensor',
        ha_subtype: entry.ha_subtype || '',
      };
      this._validation = { valid: false, message: '' };
      this._scheduleValidation();
      const content = this.shadowRoot.getElementById('tab-content');
      content.innerHTML = this._renderRulesTab();
      this._wireRulesTab();
      return;
    }
    const deleteRule = ev.target.closest('[data-delete-rule]');
    if (deleteRule) {
      this._deleteRule(deleteRule.dataset.deleteRule);
      return;
    }
    const cancel = ev.target.closest('[data-cancel-rule]');
    if (cancel) {
      this._ruleForm = null;
      this._validation = { valid: false, message: '' };
      this._confirmDelete = null;
      const content = this.shadowRoot.getElementById('tab-content');
      content.innerHTML = this._renderRulesTab();
      this._wireRulesTab();
      return;
    }
    if (ev.target.id === 'rule-save') {
      this._saveRules();
      return;
    }
    if (ev.target.closest('[data-retry="mapping"]')) {
      this._mappingError = null;
      this._loadMapping();
    }
  }

  _onRulesInput(ev) {
    const form = this._ruleForm;
    if (!form) {
      return;
    }
    if (ev.target.id === 'rule-usage-id') {
      form.usage_id = ev.target.value.trim();
    } else if (ev.target.id === 'rule-name') {
      form.justification = ev.target.value;
    } else if (ev.target.id === 'rule-entity') {
      form.ha_entity = ev.target.value;
    } else if (ev.target.id === 'rule-subtype') {
      form.ha_subtype = ev.target.value;
    } else {
      return;
    }
    this._saveState = null;
    this._scheduleValidation();
    this._updateRuleFormState();
  }

  _yamlDump(obj) {
    /** Serialize a dict-of-dicts-of-scalars fragment for validation.
     * The panel only validates the edited rule; the full document is
     * validated server-side at save time. */
    const lines = [];
    const scalar = (value) => JSON.stringify(String(value));
    const walk = (node, indent) => {
      for (const [key, value] of Object.entries(node)) {
        const pad = ' '.repeat(indent);
        if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
          if (Object.keys(value).length === 0) {
            lines.push(`${pad}${scalar(key)}: {}`);
          } else {
            lines.push(`${pad}${scalar(key)}:`);
            walk(value, indent + 2);
          }
        } else {
          lines.push(`${pad}${scalar(key)}: ${scalar(value)}`);
        }
      }
    };
    walk(obj, 0);
    return lines.join('\n') + '\n';
  }
}

if (!customElements.get('eedomus-config-panel')) {
  customElements.define('eedomus-config-panel', EedomusConfigPanel);
}
