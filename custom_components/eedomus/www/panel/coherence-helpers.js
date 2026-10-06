/**
 * Pure helpers and constants of the Coherence tab (CAP-6/7/8).
 *
 * Real ES module imported by www/panel/coherence.js (story 4.4
 * split): every pure function and constant of the tab lives here,
 * bodies byte-identical to the former single-file module — only the
 * exports were added. The tab module re-exports the entry-consumed
 * helpers; the node harness loads this file through the same
 * recursive-DFS mini-loader as every other module.
 */

import { escapeHtml, truncateDetailText } from './shared.js';

// Coherence signals (CAP-6): exact strings from eedomus/get_coherence,
// one chip per signal — glyph + label, never color alone (DESIGN.md).
// labelKey resolves at render time through t() (CAP-3).
export const COHERENCE_SIGNALS = {
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
export const COHERENCE_OK_SIGNAL = {
  labelKey: 'panel.coherence.chips.coherent',
  icon: '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>',
};
// Shared by the coherence table head generator and its skeleton (sweep)
// so the columns cannot drift: key is the sort key, labelKey the
// panel.* column label resolved at render time (CAP-3).
export const COHERENCE_COLUMNS = [
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
export const COHERENCE_NARROW_PX = 900;

// Sort direction indicator: the arrow carries the direction visually,
// aria-sort on the header cell carries the state (EXPERIENCE.md).
export const SORT_ARROW_ASC =
  '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M12 5l7 9H5z"/></svg>';
export const SORT_ARROW_DESC =
  '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M12 19l-7-9h14z"/></svg>';

// ---- Coherence pure helpers (ticket 2.3) ----
// Top-level and this-free: pure functions over the payload + tab state,
// exercised directly by tests/js/test-coherence.js.

// "To verify" predicate: any signal counts, including unknown strings.
export function coherenceToVerify(row) {
  return (row.signals || []).length > 0;
}

// Mapping identity first: the coherence table shows what was mapped, the
// effective platform/class is only the fallback.
export function coherenceType(row) {
  return [row.ha_entity || row.platform, row.ha_subtype || row.device_class]
    .filter(Boolean)
    .join(' / ');
}

// Statut tie-break severity: en_erreur first, then douteux, then
// sans_entite, then regle_active; unknown signal strings rank last.
export const COHERENCE_SIGNAL_SEVERITY = [
  'en_erreur',
  'douteux',
  'sans_entite',
  'regle_active',
];

export function coherenceSeverity(signals) {
  let severity = COHERENCE_SIGNAL_SEVERITY.length;
  for (const signal of signals) {
    const rank = COHERENCE_SIGNAL_SEVERITY.indexOf(signal);
    if (rank !== -1 && rank < severity) {
      severity = rank;
    }
  }
  return severity;
}

export function coherenceSortValue(row, key) {
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

export function coherenceCompare(a, b, key) {
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
export function filterCoherenceRows(rows, state) {
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
export function nextCoherenceSort(sort, key) {
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
export function coherenceHeadHtml(sort, t) {
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
export function coherenceFieldValue(value) {
  return value == null || value === '' ? null : String(value);
}

// "Live state" fields. A row without an entity shows
// "no entity" and no current value (edge-case matrix).
export function coherenceLiveFields(row, t) {
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
export function coherenceIdentityFields(row, t) {
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
export function coherenceRawPairs(raw) {
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
export function coherenceRawJson(raw) {
  return JSON.stringify(raw === undefined ? null : raw, null, 2);
}

// Anchor the popover under the trigger cell, flip above when there is
// strictly more room there, clamp so it never leaves the viewport
// (8 px margin). Pure: the DOM only supplies the rects.
export function coherencePopoverPosition(anchor, pop, viewport) {
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
export function coherenceTriggerHtml(periphId, expanded, controlsId, t) {
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
export function coherenceHasEntity(entityId) {
  return entityId != null && String(entityId).trim() !== '';
}

// Entity cell of the coherence table (ticket 2.6, CAP-8): an inline
// text link — accent, underlined, no button chrome — whose visible
// label is the entity itself. The accessible name carries the action
// and the destination, mirroring the detail's "View in HA".
// A row without an entity keeps its inert "no entity".
export function coherenceEntityLinkHtml(entityId, t) {
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
export function coherenceDetailAttempts(attempts, t) {
  const count = Number(attempts);
  const key = count === 1
    ? 'panel.coherence.detail.attempts_one'
    : 'panel.coherence.detail.attempts_other';
  return ` ${t(key, { n: escapeHtml(attempts) })}`;
}

// Detail body shared by the desktop popover (2.4) and the mobile
// expanded row (2.5): the same sections from the same coherence row,
// no re-fetch. Everything is eedomus-sourced and escaped.
export function coherenceDetailHtml(row, t) {
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

export function coherenceDetailFieldsHtml(fields, t) {
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

export function coherenceDetailPairsHtml(pairs) {
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
export const POPOVER_FOCUSABLE_SELECTOR = [
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
export function hoverCapable() {
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
export function nextCoherenceExpanded(currentId, tappedId) {
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
export function coherenceIsExpanded(row, expandedId, narrow) {
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
export function coherenceExpandedRowHtml(row, t) {
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
export function coherenceRowExpansionHtml(row, expandedId, narrow, t) {
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
export function coherenceChipsHtml(row, t) {
  const signals = (row && row.signals) || [];
  if (signals.length === 0) {
    return coherenceChipHtml('coherent', row, t);
  }
  return signals
    .map((signal) => coherenceChipHtml(signal, row, t))
    .join('');
}

export function coherenceChipHtml(signal, row, t) {
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
export function coherenceRowHtml(row, expandedId, narrow, t) {
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

