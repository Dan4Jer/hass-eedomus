/**
 * Cross-tab pieces of the Eedomus config panel.
 *
 * Real ES module imported by www/eedomus-panel.js (the entry keeps its
 * URL and re-exports nothing): the transverse constants (tab ids,
 * announce and timeout delays), the escaping and status-line pure
 * helpers, and the shared prototype mixin (debounced announcements,
 * escaping, coherence cache invalidation). Pure extraction of the
 * former single-file panel — the code moved as-is.
 */

export const TABS = [
  'supervision',
  'peripheriques',
  'regles',
  'historique',
  'coherence',
];

// Debounce of the result-count announcement (sweep): a burst of typing
// in either search field produces ONE screen-reader announcement, once
// typing pauses for this delay. The visible filtering stays real-time.
export const SEARCH_ANNOUNCE_DELAY_MS = 300;

// Ceiling of a clipboard write: a permission prompt abandoned by the
// user never settles — the race converts it into an announced failure.
export const COPY_WRITE_TIMEOUT_MS = 2000;

// Ceiling of the get_translations call: a dropped websocket never
// settles — the race frees the loading slot so the next set hass can
// retry instead of waiting on a dead request forever.
export const STRINGS_LOAD_TIMEOUT_MS = 10000;

// Status-line texts (sweep): one pure helper per tab so the immediate
// render path and the debounced announcement compute the exact same
// message — the live region never disagrees with the table.
export function periphStatusText(total, shown, touchedOnly, t) {
  // One/other splits (same convention as the attempts detail): a
  // count of 1 takes the singular form in every locale — the plain
  // total and the filter suffix alike.
  const filterLabel = touchedOnly
    ? ` ${t(shown === 1
        ? 'panel.peripheriques.status.filtered_one'
        : 'panel.peripheriques.status.filtered_other', { n: shown })}`
    : '';
  const totalKey = total === 1
    ? 'panel.peripheriques.status.total_one'
    : 'panel.peripheriques.status.total_other';
  return t(totalKey, { n: total }) + filterLabel;
}

export function coherenceStatusText(shown, search, view, t) {
  if (shown === 0 && search) {
    return t('panel.coherence.status.no_result', { q: search });
  }
  if (shown === 0 && view === 'to_verify') {
    return t('panel.coherence.status.all_clear');
  }
  // One/other splits (same convention as the attempts detail).
  const viewLabel = view === 'to_verify'
    ? ` ${t(shown === 1
        ? 'panel.coherence.status.filtered_one'
        : 'panel.coherence.status.filtered_other', { n: shown })}`
    : '';
  const totalKey = shown === 1
    ? 'panel.coherence.status.total_one'
    : 'panel.coherence.status.total_other';
  return t(totalKey, { n: shown }) + viewLabel;
}

// HTML escaping shared by every markup builder below (the _escapeHtml
// method delegates here so the class never diverges).
export function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// Truncation of an error detail for display (visible + accessible
// text — the full message lives in the title). Shared by the
// coherence chips and the supervision backfill rows: ONE copy, same
// 40-char contract. Truncation walks code points (Array.from) so a
// surrogate pair (an emoji) is never cut mid-pair.
export function truncateDetailText(text, max) {
  const value = String(text);
  const chars = Array.from(value);
  if (chars.length <= max) {
    return value;
  }
  return `${chars.slice(0, max - 1).join('')}…`;
}

// Backfill progress indicator (story 110): a thin bar plus its
// textual equivalent — the two surfaces (Supervision queue row and
// Coherence detail) render the SAME object with the SAME keys
// (popover/extended-line parity). Pure: the translator is injected,
// every value comes from the backend payload, the panel never
// recomputes (CAP-9: the panel displays).
export function backfillProgressHtml(progress, t) {
  const retrieved =
    progress && typeof progress.retrieved_points === 'number'
      ? progress.retrieved_points
      : null;
  if (retrieved === null) {
    // No progress entry yet: no indicator, never a fake empty bar
    return '';
  }
  const total =
    progress && typeof progress.total_points === 'number'
      ? progress.total_points
      : null;
  const oldest =
    progress && progress.oldest_timestamp
      ? new Date(progress.oldest_timestamp)
      : null;
  const date =
    oldest !== null && !Number.isNaN(oldest.getTime())
      ? oldest.toLocaleDateString()
      : null;
  let textKey;
  let textParams;
  if (retrieved === 0) {
    textKey = 'panel.backfill.progress.not_started';
    textParams = {};
  } else if (total) {
    textKey = date
      ? 'panel.backfill.progress.text'
      : 'panel.backfill.progress.text_no_date';
    textParams = { retrieved, total, date };
  } else {
    textKey = date
      ? 'panel.backfill.progress.text_no_estimate'
      : 'panel.backfill.progress.text_no_estimate_no_date';
    textParams = { retrieved, date };
  }
  const fraction = total && total > 0 ? retrieved / total : 0;
  const pct = Math.max(0, Math.min(100, Math.round(fraction * 100)));
  const fill = retrieved > 0
    ? `<span class="progress-fill" style="width: ${pct}%"></span>`
    : '';
  return `
    <span class="backfill-progress">
      <span class="progress-track" aria-hidden="true">${fill}</span>
      <span class="progress-text">${escapeHtml(t(textKey, textParams))}</span>
    </span>
  `;
}

// The progress bar styles, shared by both surfaces (each tab's style
// constant embeds this block — same classes, same look, parity).
export const BACKFILL_PROGRESS_STYLES = `
  .backfill-progress { display: flex; flex-direction: column; gap: 2px; }
  .progress-track {
    display: block; height: 4px; border-radius: 2px;
    background: var(--divider-color); overflow: hidden;
  }
  .progress-fill {
    display: block; height: 100%;
    background: var(--primary-color); border-radius: 2px;
  }
  .progress-text { font-size: 11px; opacity: 0.8; }
`;

export function applySharedMixin(EedomusConfigPanel) {
  Object.assign(EedomusConfigPanel.prototype, {
  // Result-count announcements (sweep). The visible count element
  // updates with every render (it must never lag the filtering); only
  // the sr-only live region is debounced, so a typing burst yields
  // one announcement from the same pure message helper as the render.
  _cancelStatusAnnounce(statusId) {
    if (statusId && this._statusAnnounceTimers[statusId]) {
      clearTimeout(this._statusAnnounceTimers[statusId]);
      delete this._statusAnnounceTimers[statusId];
    }
  },

  _debounceStatusAnnounce(statusId, announce) {
    // One shared timer per live region, cancelled on every keystroke:
    // a typing burst collapses into a single post-pause announcement.
    this._cancelStatusAnnounce(statusId);
    this._statusAnnounceTimers[statusId] = setTimeout(() => {
      delete this._statusAnnounceTimers[statusId];
      announce();
    }, SEARCH_ANNOUNCE_DELAY_MS);
  },

  _announceStatusNow(live, text) {
    // An immediate announce (sort, toggle, Escape) cancels any pending
    // debounced one so the two paths never double-fire.
    this._cancelStatusAnnounce(live.id);
    live.textContent = text;
  },

  _escapeHtml(value) {
    return escapeHtml(value);
  },

  _escapeAttr(value) {
    return this._escapeHtml(value);
  },

  // Coherence cache invalidation: every mapping write (rule save,
  // delete, YAML save, restore) changes what the coherence view
  // derives — the next visit to the tab reloads the signals instead
  // of showing stale rows until a full panel reload. The generation
  // bump also discards any load still in flight: its data predates
  // the write and must not repopulate the cache.
  _invalidateCoherenceCache() {
    this._coherenceGeneration += 1;
    this._coherence = null;
    this._coherenceError = null;
  },
  });
}

/**
 * Menu button (issue #125 / ticket 116): the escape affordance for
 * narrow viewports. Custom panels get no HA app-header, so when HA
 * hides the sidebar the panel must offer its own way out — this
 * button opens HA's drawer (the click handler in the entry dispatches
 * the standard `hass-toggle-menu` event).
 *
 * The 900px media value equals COHERENCE_NARROW_PX
 * (coherence-helpers.js); the node test pins the equality — no new
 * breakpoint (EXPERIENCE.md, Responsive).
 */
export function menuButtonHtml(t) {
  const label = escapeHtml(t('panel.menu.aria'));
  return (
    `<button class="menu-button" data-action="toggle-menu"` +
    ` aria-label="${label}">` +
    `<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">` +
    `<path fill="currentColor" ` +
    `d="M3,6h18v2H3V6z M3,11h18v2H3V11z M3,16h18v2H3V16z" />` +
    `</svg></button>`
  );
}

export const MENU_BUTTON_STYLES = `
  /* Menu button (#125): hidden on wide viewports — the HA sidebar is
     permanently visible there and a second exit would be noise. */
  .menu-button {
    display: none;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    margin: 4px 0 0 -8px;
    padding: 0;
    border: none;
    border-radius: var(--ha-border-radius, 4px);
    background: transparent;
    color: var(--primary-text-color);
    cursor: pointer;
  }
  .menu-button:focus-visible {
    outline: var(--ha-focus-outline, 2px solid currentColor);
  }
  @media (max-width: 900px) {
    .menu-button { display: inline-flex; }
  }
`;
