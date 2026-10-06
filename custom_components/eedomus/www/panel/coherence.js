/**
 * Coherence tab of the Eedomus config panel (CAP-6/7/8).
 *
 * Real ES module imported by www/eedomus-panel.js: the coherence pure
 * helpers, the tab's stylesheet chunk and the coherence prototype
 * mixin. Pure extraction of the former single-file panel — the code
 * moved as-is.
 */

import { escapeHtml, coherenceStatusText, truncateDetailText } from './shared.js';

// Coherence signals (CAP-6): exact strings from eedomus/get_coherence,
// one chip per signal — glyph + label, never color alone (DESIGN.md).
// labelKey resolves at render time through t() (CAP-3).
const COHERENCE_SIGNALS = {
  sans_entite: {
    labelKey: 'panel.coherence.chips.sans_entite',
    icon: '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M12 2C6.47 2 2 6.47 2 12s4.47 10 10 10 10-4.47 10-10S17.53 2 12 2zm5 13.59L15.59 17 12 13.41 8.41 17 7 15.59 10.59 12 7 8.41 8.41 7 12 10.59 15.59 7 17 8.41 13.41 12 17 15.59z"/></svg>',
  },
  douteux: {
    labelKey: 'panel.coherence.chips.douteux',
    icon: '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>',
  },
  regle_active: {
    labelKey: 'panel.coherence.chips.regle_active',
    icon: '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M3 17v2h6v-2H3zM3 5v2h10V5H3zm10 16v-2h8v-2h-8v-2h-2v6h2zM7 9v2H3v2h4v2h2V9H7zm14 4v-2H11v2h10zm-4-4h2V7h4V5h-4V3h-2v6z"/></svg>',
  },
  en_erreur: {
    labelKey: 'panel.coherence.chips.en_erreur',
    icon: '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M12 6v3l4-4-4-4v3c-4.42 0-8 3.58-8 8 0 1.57.46 3.03 1.24 4.26L6.7 14.8c-.45-.83-.7-1.79-.7-2.8 0-3.31 2.69-6 6-6zm6.76 1.74L17.3 9.2c.44.84.7 1.8.7 2.8 0 3.31-2.69 6-6 6v-3l-4 4 4 4v-3c4.42 0 8-3.58 8-8 0-1.57-.46-3.03-1.24-4.26z"/></svg>',
  },
};
const COHERENCE_OK_SIGNAL = {
  labelKey: 'panel.coherence.chips.coherent',
  icon: '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>',
};
// Shared by the coherence table head generator and its skeleton (sweep)
// so the columns cannot drift: key is the sort key, labelKey the
// panel.* column label resolved at render time (CAP-3).
const COHERENCE_COLUMNS = [
  { key: 'periph_id', labelKey: 'panel.coherence.columns.periph_id' },
  { key: 'name', labelKey: 'panel.coherence.columns.name' },
  { key: 'entity_id', labelKey: 'panel.coherence.columns.entity_id' },
  { key: 'type', labelKey: 'panel.coherence.columns.type' },
  { key: 'status', labelKey: 'panel.coherence.columns.status' },
];
// The single breakpoint of the coherence tab (ticket 2.5): the JS
// surface switch (coherenceNarrowView, matchMedia) and the CSS
// reflow (@media in _render — cross-referenced there) both derive
// from it — one breakpoint, two surfaces.
const COHERENCE_NARROW_PX = 900;

// Sort direction indicator: the arrow carries the direction visually,
// aria-sort on the header cell carries the state (EXPERIENCE.md).
const SORT_ARROW_ASC =
  '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M12 5l7 9H5z"/></svg>';
const SORT_ARROW_DESC =
  '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M12 19l-7-9h14z"/></svg>';

// ---- Coherence pure helpers (ticket 2.3) ----
// Top-level and this-free: pure functions over the payload + tab state,
// exercised directly by tests/js/test-coherence.js.

// "To verify" predicate: any signal counts, including unknown strings.
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

// Sort cycle: ascending -> descending -> neutral (response order).
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
function coherenceHeadHtml(sort, t) {
  const cells = COHERENCE_COLUMNS.map((col) => {
    const label = t(col.labelKey);
    const active = sort.key === col.key;
    const ariaSort = !active
      ? 'none'
      : sort.dir === 'asc' ? 'ascending' : 'descending';
    const stateLabel = !active
      ? ''
      : sort.dir === 'asc'
        ? t('panel.coherence.sort.aria_asc')
        : t('panel.coherence.sort.aria_desc');
    const ariaText = t('panel.coherence.sort.aria', { label }) + stateLabel;
    const arrow = !active
      ? ''
      : sort.dir === 'asc'
        ? `<span class="sort-arrow">${SORT_ARROW_ASC}</span>`
        : `<span class="sort-arrow">${SORT_ARROW_DESC}</span>`;
    return `
          <th scope="col" aria-sort="${ariaSort}">
            <button class="sort-header" type="button" data-sort-key="${col.key}"
                    aria-label="${escapeHtml(ariaText)}">
              ${label}${arrow}
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

// ---- Popover pure helpers (ticket 2.4) ----
// Same contract as the helpers above: top-level, this-free, exercised
// by tests/js/test-coherence.js. The popover makes no network call —
// everything renders from the already-loaded coherence row.

// Shared value normalizer of the detail fields: null/undefined/empty
// stays null (the renderer shows the catalog's unknown-value text) —
// a missing field is information, never a silent hole.
function coherenceFieldValue(value) {
  return value == null || value === '' ? null : String(value);
}

// "Live state" fields. A row without an entity shows
// "no entity" and no current value (edge-case matrix).
function coherenceLiveFields(row, t) {
  const hasEntity = Boolean(row.entity_id);
  return [
    {
      label: t('panel.coherence.detail.entity_id'),
      value: hasEntity
        ? String(row.entity_id)
        : t('panel.common.no_entity'),
      mono: true,
    },
    {
      label: t('panel.coherence.detail.current_value'),
      value: hasEntity ? coherenceFieldValue(row.state) : null,
    },
    {
      label: t('panel.coherence.detail.usage_id'),
      value: coherenceFieldValue(row.usage_id),
      mono: true,
    },
    {
      label: t('panel.coherence.detail.parent'),
      value: coherenceFieldValue(row.parent_periph_id),
      mono: true,
    },
    {
      label: t('panel.coherence.detail.last_update'),
      value: coherenceFieldValue(row.last_update),
    },
  ];
}

// Mapping identity fields: what was mapped and why.
function coherenceIdentityFields(row, t) {
  return [
    {
      label: t('panel.coherence.detail.ha_entity'),
      value: coherenceFieldValue(row.ha_entity),
      mono: true,
    },
    {
      label: t('panel.coherence.detail.ha_subtype'),
      value: coherenceFieldValue(row.ha_subtype),
      mono: true,
    },
    {
      label: t('panel.coherence.detail.justification'),
      value: coherenceFieldValue(row.justification),
    },
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

// Raw JSON text of the payload (UX run 3): pretty-printed with indent
// 2, keys in the payload's original order — JSON.stringify never
// sorts, the sorted list above stays the first level. A null payload
// renders the honest "null", never the string "undefined".
function coherenceRawJson(raw) {
  return JSON.stringify(raw === undefined ? null : raw, null, 2);
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


// Trigger of the periph_id cell: the only element of the row that
// opens the detail, carrying its accessible name. The template
// carries aria-expanded only — the popover wiring sets
// aria-haspopup="dialog" dynamically (the narrow surface is an
// inline row, not a dialog), and `controlsId` points at the
// expansion row when it exists (2.5).
function coherenceTriggerHtml(periphId, expanded, controlsId, t) {
  const controls = controlsId
    ? ` aria-controls="${escapeHtml(controlsId)}"`
    : '';
  return `
    <button class="coherence-id-trigger" type="button"
            data-coherence-popover="${escapeHtml(periphId)}"
            aria-expanded="${expanded ? 'true' : 'false'}"${controls}
            aria-label="${escapeHtml(t('panel.coherence.trigger.aria', {
              periph_id: periphId,
            }))}">
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
// and the destination, mirroring the detail's "View in HA".
// A row without an entity keeps its inert "no entity".
function coherenceEntityLinkHtml(entityId, t) {
  if (!coherenceHasEntity(entityId)) {
    return `<em>${t('panel.common.no_entity')}</em>`;
  }
  return `<a class="entity-link" href="#"
            data-entity-id="${escapeHtml(entityId)}"
            aria-label="${escapeHtml(t('panel.coherence.entity_link.aria', {
              entity_id: entityId,
            }))}"
           >${escapeHtml(entityId)}</a>`;
}

// Attempts detail of the error state: 1 takes the singular form,
// everything else (a non-numeric value included) the plural — the
// count only interpolates, a non-numeric value never renders NaN.
function coherenceDetailAttempts(attempts, t) {
  const count = Number(attempts);
  const key = count === 1
    ? 'panel.coherence.detail.attempts_one'
    : 'panel.coherence.detail.attempts_other';
  return ` ${t(key, { n: escapeHtml(attempts) })}`;
}

// Detail body shared by the desktop popover (2.4) and the mobile
// expanded row (2.5): the same sections from the same coherence row,
// no re-fetch. Everything is eedomus-sourced and escaped.
function coherenceDetailHtml(row, t) {
  const errorHtml = row.error_message
    ? `<p class="popover-error">
         ${t('panel.coherence.detail.error_message', {
           error_message: escapeHtml(row.error_message),
         })}
         ${row.retry_after
           ? ` ${t('panel.coherence.detail.retry_after', {
               retry_after: escapeHtml(row.retry_after),
             })}`
           : ''}
         ${row.attempts != null
           ? coherenceDetailAttempts(row.attempts, t)
           : ''}
       </p>`
    : '';
  return `
      <div class="popover-head">
        <span class="popover-name">${escapeHtml(row.name || '')}</span>
        <code class="popover-id">${escapeHtml(row.periph_id)}</code>
      </div>
      <div class="popover-section">
        <h3 class="popover-heading">${t(
          'panel.coherence.detail.section_live'
        )}</h3>
        ${errorHtml}
        <dl>${coherenceDetailFieldsHtml(coherenceLiveFields(row, t), t)}</dl>
      </div>
      <div class="popover-section">
        <h3 class="popover-heading">${t(
          'panel.coherence.detail.section_identity'
        )}</h3>
        <dl>${coherenceDetailFieldsHtml(coherenceIdentityFields(row, t), t)}</dl>
      </div>
      <div class="popover-actions">
        <button class="row-action" type="button"
                data-periph-id="${escapeHtml(row.periph_id)}"
                data-usage-id="${escapeHtml(row.usage_id || '')}">
          ${t('panel.coherence.detail.create_rule')}
        </button>
        ${coherenceHasEntity(row.entity_id)
          ? `<button class="row-action" type="button"
                     data-entity-id="${escapeHtml(row.entity_id)}"
                     aria-label="${escapeHtml(t(
                       'panel.coherence.entity_link.aria',
                       { entity_id: row.entity_id }
                     ))}">
               ${t('panel.coherence.detail.view_in_ha')}
             </button>`
          : ''}
      </div>
      <details class="popover-raw">
        <summary>${t('panel.coherence.detail.raw_summary')}</summary>
        <dl>${coherenceDetailPairsHtml(coherenceRawPairs(row.raw))}</dl>
        <div class="raw-json-bar">
          <button class="row-action copy-json" type="button"
                  data-copy-json="1">
            ${t('panel.coherence.detail.copy_json')}
          </button>
        </div>
        <p class="sr-only" id="copy-status-live" role="status"></p>
        <pre class="raw-json"><code>${escapeHtml(
          coherenceRawJson(row.raw)
        )}</code></pre>
      </details>
    `;
}

function coherenceDetailFieldsHtml(fields, t) {
  return fields
    .map((field) => {
      let valueHtml;
      if (field.value == null) {
        valueHtml = `<em class="detail-unknown">${t(
          'panel.common.unknown_value'
        )}</em>`;
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
export function coherenceNarrowMedia() {
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

export function coherenceNarrowView() {
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
export function coherenceExpandedRowId(periphId) {
  return `coherence-expanded-${String(periphId)}`;
}

// The expansion row itself: the shared detail body (strict parity
// with the popover) inside the table reflow, spanning every column.
function coherenceExpandedRowHtml(row, t) {
  return `
      <tr class="coherence-expanded-row"
          id="${escapeHtml(coherenceExpandedRowId(row.periph_id))}">
        <td colspan="${COHERENCE_COLUMNS.length}">
          <div class="coherence-expanded-body">${coherenceDetailHtml(row, t)}</div>
        </td>
      </tr>
    `;
}

// Composed detail surface of one row: the trigger (aria-expanded
// reflecting the state, aria-controls only when the target exists)
// and the expansion row when the predicate says so — nothing of it
// otherwise (the wide side never emits an expansion).
function coherenceRowExpansionHtml(row, expandedId, narrow, t) {
  const expanded = coherenceIsExpanded(row, expandedId, narrow);
  return {
    expanded,
    rowClass: expanded ? ' class="coherence-row-expanded"' : '',
    trigger: coherenceTriggerHtml(
      row.periph_id,
      expanded,
      expanded ? coherenceExpandedRowId(row.periph_id) : null,
      t
    ),
    expansion: expanded ? coherenceExpandedRowHtml(row, t) : '',
  };
}

// Chips of the Status cell: one chip per signal, "consistent" when
// there is none; an unknown string keeps a neutral chip carrying
// the raw value — never dropped, never "consistent".
function coherenceChipsHtml(row, t) {
  const signals = (row && row.signals) || [];
  if (signals.length === 0) {
    return coherenceChipHtml('coherent', row, t);
  }
  return signals
    .map((signal) => coherenceChipHtml(signal, row, t))
    .join('');
}

function coherenceChipHtml(signal, row, t) {
  const known = signal === 'coherent' || Boolean(COHERENCE_SIGNALS[signal]);
  const def = signal === 'coherent'
    ? COHERENCE_OK_SIGNAL
    : COHERENCE_SIGNALS[signal] || null;
  let label;
  let title = '';
  if (signal === 'en_erreur' && row && row.error_message) {
    // The retry detail is visible (truncated), in the accessible name,
    // and complete in the title — never color or title alone.
    const detail = truncateDetailText(row.error_message, 40);
    label = t('panel.coherence.chips.en_erreur_detail', { truncated: detail });
    title = ` title="${escapeHtml(
      t('panel.coherence.chips.error_title', { msg: row.error_message })
    )}"`;
  } else if (def) {
    label = t(def.labelKey);
  } else {
    label = t('panel.coherence.chips.unknown', { raw: signal });
  }
  const icon = def ? def.icon : '';
  return `
      <span class="coherence-chip coherence-chip-${known ? signal : 'unknown'}"${title}
            aria-label="${escapeHtml(label)}">
        ${icon}
        ${escapeHtml(label)}
      </span>
    `;
}

// Composed table row (2.6 extraction): the trigger, the entity link
// (CAP-8), type and chips, plus the expansion carried by
// coherenceRowExpansionHtml — pure over the payload + the volatile
// state, like the rest of the composition.
function coherenceRowHtml(row, expandedId, narrow, t) {
  const type = coherenceType(row);
  // CAP-8: the entity is an inline text link to the standard
  // HA surface — inert "no entity" when there is none.
  const entity = coherenceEntityLinkHtml(row.entity_id, t);
  const detail = coherenceRowExpansionHtml(row, expandedId, narrow, t);
  return `
      <tr${detail.rowClass}>
        <td class="coherence-id" data-label="${escapeHtml(t(
          'panel.coherence.cell_labels.periph_id'
        ))}">
          ${detail.trigger}
        </td>
        <td data-label="${escapeHtml(t('panel.coherence.columns.name'))}">${escapeHtml(
    row.name || ''
  )}</td>
        <td class="ha-entity" data-label="${escapeHtml(t(
          'panel.coherence.columns.entity_id'
        ))}">${entity}</td>
        <td data-label="${escapeHtml(t('panel.coherence.columns.type'))}">${escapeHtml(
    type
  )}</td>
        <td data-label="${escapeHtml(t('panel.coherence.columns.status'))}">
          <div class="coherence-chips">${coherenceChipsHtml(row, t)}</div>
        </td>
      </tr>
      ${detail.expansion}
    `;
}

export const COHERENCE_STYLES = `
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

        /* Entity link (2.6, CAP-8): inline text link — accent,
           underlined, never button chrome; distinct from
           the popover trigger (dotted). */
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
        .popover-raw .raw-json-bar { margin-top: 8px; }
        .popover-raw .raw-json {
          margin: 4px 0 8px; padding: 8px;
          background: var(--input-fill-color, var(--card-background-color));
          border-radius: var(--ha-card-border-radius, 12px);
          overflow-x: auto;
          color: var(--primary-text-color);
          font-size: 12px;
        }
        .popover-raw .raw-json code {
          font-family: var(--code-font-family, ui-monospace, Menlo, monospace);
          white-space: pre;
        }

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
             sticky wrapping bar of sort buttons, still sticky while
             scrolling. */
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

          /* Expanded row (2.5): content parity with the popover,
             different surface — the row + extension pair reads as
             one unit under the finger, the extension lives in the
             block reflow (never a silent horizontal scroll). */
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
`;

export function applyCoherenceMixin(EedomusConfigPanel) {
  Object.assign(EedomusConfigPanel.prototype, {
  // ================= Coherence (ticket 2.2) =================

  async _loadCoherence() {
    if (!this._hass || this._coherenceLoading) {
      return;
    }
    this._coherenceLoading = true;
    this._coherenceError = null;
    this._coherence = null;
    // Generation captured at load start: a write that invalidates the
    // cache while the request is in flight bumps the generation — this
    // (stale) resolution is then discarded, never written back.
    const generation = this._coherenceGeneration;
    if (this._tab === 'coherence') {
      const content = this.shadowRoot.getElementById('tab-content');
      if (content) {
        // Retry shows the loading state again, never a stale table/error.
        content.innerHTML = this._renderCoherenceTab();
      }
    }
    let rows = null;
    try {
      const result = await this._hass.callWS({
        type: 'eedomus/get_coherence',
      });
      rows = (result && result.peripherals) || [];
    } catch (err) {
      rows = null;
      if (generation === this._coherenceGeneration) {
        this._coherenceError = (err && (err.message || err.code)) ||
          'panel.common.command_refused';
      }
    }
    this._coherenceLoading = false;
    if (generation !== this._coherenceGeneration) {
      // The cache was invalidated while this request was in flight:
      // the resolution predates the write — dropped, the next visit
      // reloads.
      return;
    }
    this._coherence = rows;
    if (this._tab === 'coherence') {
      const content = this.shadowRoot.getElementById('tab-content');
      if (content) {
        content.innerHTML = this._renderCoherenceTab();
        this._renderCoherenceTable();
      }
    }
  },

  _renderCoherenceTab() {
    if (this._coherenceError) {
      return `
        <div class="state-message" role="alert">
          ${this.t('panel.coherence.error.load', {
            err: this._escapeHtml(this.t(this._coherenceError)),
          })}
          <br>
          <button class="retry" type="button" data-retry="coherence">
            ${this.t('panel.common.retry')}
          </button>
        </div>
      `;
    }
    if (this._coherence === null) {
      return this._renderCoherenceSkeleton();
    }
    if (this._coherence.length === 0) {
      return `
        <div class="state-message">
          ${this.t('panel.coherence.empty')}
        </div>
      `;
    }
    return `
      ${this._renderCoherenceToolbar()}
      <p class="result-count" id="coherence-status"></p>
      <p class="sr-only" id="coherence-status-live" role="status"></p>
      <div id="coherence-body"></div>
    `;
  },

  _renderCoherenceToolbar() {
    const toVerify = (this._coherence || []).filter(coherenceToVerify).length;
    return `
      <div class="toolbar">
        <div class="search">
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M15.5 14h-.79l-.28-.27a6.5 6.5 0 1 0-.7.7l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0A4.5 4.5 0 1 1 14 9.5 4.5 4.5 0 0 1 9.5 14z"/></svg>
          <input id="coherence-search" type="search"
                 placeholder="${this._escapeHtml(
                   this.t('panel.coherence.search.placeholder')
                 )}"
                 aria-label="${this._escapeHtml(
                   this.t('panel.coherence.search.aria')
                 )}"
                 value="${this._escapeHtml(this._coherenceSearch)}">
        </div>
        <button class="filter-touches" type="button" data-coherence-view="to_verify"
                aria-pressed="${this._coherenceView === 'to_verify'}">
          ${this.t('panel.coherence.filter.label')}
          <span class="count">
            ${this.t('panel.coherence.filter.count', { n: toVerify })}
          </span>
        </button>
      </div>
    `;
  },

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
    // Any reshuffle (sort, filter, search, toggle) can remove the
    // anchor row: the popover closes, never floats orphaned.
    this._closeCoherencePopover();
    // Keep the view toggle in sync (mirror of the Peripherals filter).
    const viewBtn = root.querySelector('[data-coherence-view]');
    if (viewBtn) {
      viewBtn.setAttribute(
        'aria-pressed',
        String(this._coherenceView === 'to_verify')
      );
      const countSpan = viewBtn.querySelector('.count');
      if (countSpan) {
        const toVerify = (this._coherence || []).filter(coherenceToVerify).length;
        countSpan.textContent = this.t('panel.coherence.filter.count', {
          n: toVerify,
        });
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
    // Never an orphaned extension: the expanded row absent from the
    // filtered result closes the mobile state along with the body.
    if (
      this._coherenceExpandedId !== null &&
      !rows.some((r) => String(r.periph_id) === this._coherenceExpandedId)
    ) {
      this._coherenceExpandedId = null;
    }
    const statusText = coherenceStatusText(
      rows.length,
      this._coherenceSearch,
      this._coherenceView,
      this._t
    );
    if (rows.length === 0 && this._coherenceSearch) {
      // Explicit no-result state, announced — never a silent empty table.
      status.textContent = statusText;
      if (announceStatus && live) {
        this._announceStatusNow(live, statusText);
      }
      body.innerHTML = `
        <div class="state-message">
          ${this.t('panel.coherence.empty.search', {
            q: this._escapeHtml(this._coherenceSearch),
          })}
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
          ${this.t('panel.coherence.empty.all_clear')}
          <br>
          <button class="row-action" type="button" data-coherence-show-all="1">
            ${this.t('panel.coherence.empty.show_all')}
          </button>
        </div>
      `;
      return;
    }

    body.innerHTML = `
      <div class="coherence-table-wrap">
        <table class="coherence-table">
          <caption class="sr-only">${this.t('panel.coherence.table.caption')}</caption>
          ${coherenceHeadHtml(this._coherenceSort, this._t)}
          <tbody>${rows.map((row) => this._renderCoherenceRow(row)).join('')}</tbody>
        </table>
      </div>
    `;
    status.textContent = statusText;
    if (announceStatus && live) {
      this._announceStatusNow(live, statusText);
    }
  },

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
      this._coherenceView,
      this._t
    );
  },

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
  },

  // ---- Mobile expanded row (ticket 2.5) ----
  // Under 900 px, the touch counterpart of the popover: the same
  // trigger, the same content, an inline surface in the table.

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
    // replaces the trigger — Enter at narrow width keeps operating
    // the same line, a tap never had the focus anyway.
    const restoreFocus =
      this.shadowRoot.activeElement === this._coherenceTriggerFor(id);
    // A single expanded row at a time: a re-tap closes it, a tap on
    // another row moves the extension (nextCoherenceExpanded).
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
  },

  _onCoherenceBreakpoint(ev) {
    if (ev.matches) {
      // Narrow side entered (matchMedia fires without a resize of
      // this surface): the popover is desktop-only — it closes, the
      // expanded row is the single detail surface from here on. The
      // expansion state itself survives the crossing.
      this._closeCoherencePopover();
      return;
    }
    // Wide side: the expanded row does not exist there — the popover
    // of 2.4 is the only detail surface, the state does not survive
    // the crossing (the resize listener already closed any popover).
    if (this._coherenceExpandedId !== null) {
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
  },

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
  },

  // ---- Navigation to the HA entity (ticket 2.6, CAP-8) ----
  // hass-more-info is the standard mechanism for HA custom elements
  // (verified in the live frontend bundle): a composed CustomEvent
  // that bubbles to the document, the more-info box opens the
  // entity's standard surface — web and mobile. A navigation, not
  // an editing control: no writes, no network calls.

  _openEntityMoreInfo(entityId) {
    if (!coherenceHasEntity(entityId)) {
      return;
    }
    const id = String(entityId);
    // Clean closes before the navigation: the mobile expanded row
    // and the popover do not survive the more-info opening — focus
    // returned to the trigger, never an orphaned floating
    // surface.
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
  },

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
  },

  // ---- Peripheral detail popover (ticket 2.4) ----
  // Desktop floating surface of the Coherence tab. The trigger stays
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
      // Under 900 px (2.5), the surface is the expanded row: the
      // hover never opens the popover next to it — a single
      // detail surface at a time, even a narrow window + mouse.
      return;
    }
    const trigger = ev.target.closest
      ? ev.target.closest('[data-coherence-popover]')
      : null;
    if (!trigger || trigger === openTrigger) {
      return;
    }
    this._cancelCoherenceHover();
    // A new hover intent cancels the closing grace of the previous
    // popover: sweeping from one trigger to another, the leave-timer
    // of the first would otherwise close the popover whose teardown
    // kills this pending intent — no popover would ever open.
    this._cancelCoherenceLeave();
    // Hover intent ~250 ms: no popover storm when sweeping the mouse
    // across the table. Keyboard opens without delay (Enter).
    this._coherenceHoverTrigger = trigger;
    this._coherenceHoverTimer = setTimeout(() => {
      this._coherenceHoverTimer = null;
      this._coherenceHoverTrigger = null;
      // The breakpoint may have been crossed since the intent was
      // scheduled (viewport changed during the delay, no resize on
      // this surface yet): the popover is a wide-only surface, the
      // narrow side expands a row instead.
      if (coherenceNarrowView()) {
        return;
      }
      this._openCoherencePopover(trigger, { focusPopover: false, byHover: true });
    }, 250);
  },

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
  },

  _cancelCoherenceHover() {
    if (this._coherenceHoverTimer) {
      clearTimeout(this._coherenceHoverTimer);
      this._coherenceHoverTimer = null;
    }
    this._coherenceHoverTrigger = null;
  },

  _cancelCoherenceLeave() {
    if (this._coherenceLeaveTimer) {
      clearTimeout(this._coherenceLeaveTimer);
      this._coherenceLeaveTimer = null;
    }
  },

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
      this.t('panel.coherence.trigger.popover.aria', {
        name: row.name || row.periph_id,
        periph_id: row.periph_id,
      })
    );
    pop.innerHTML = coherenceDetailHtml(row, this._t);
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
  },

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
  },

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
    // the focus lands outside the trigger and the popover (e.g. Tab
    // away from the trigger).
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
    // Escape closes and returns the focus to the trigger.
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
  },

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
  },

  _popoverFocusables(pop) {
    return Array.from(
      pop.querySelectorAll(POPOVER_FOCUSABLE_SELECTOR)
    );
  },

  _renderCoherenceSkeleton() {
    // Skeletons shaped like the expected content: table header + rows.
    // The head is the SAME generator as the loaded table (sweep) —
    // shared labels and markup, neutral sort. inert keeps the loading
    // copy out of the tab order: its buttons are placeholders, not
    // controls, and the table is aria-hidden anyway.
    const row = `
      <tr><td colspan="${COHERENCE_COLUMNS.length}"><div class="skeleton-cell" aria-hidden="true"></div></td></tr>`;
    return `
      <div class="coherence-table-wrap" role="status"
           aria-label="${this._escapeHtml(
             this.t('panel.coherence.skeleton.aria')
           )}">
        <table class="coherence-table" aria-hidden="true" inert>
          ${coherenceHeadHtml({ key: null, dir: null }, this._t)}
          <tbody>${row.repeat(8)}</tbody>
        </table>
      </div>
    `;
  },

  _renderCoherenceRow(row) {
    // Thin shell over the pure composition (2.6): the class only
    // supplies the volatile state the helpers cannot reach.
    return coherenceRowHtml(
      row,
      this._coherenceExpandedId,
      coherenceNarrowView(),
      this._t
    );
  },
  });
}
