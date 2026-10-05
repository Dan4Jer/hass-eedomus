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

export const TABS = ['peripheriques', 'regles', 'historique', 'coherence'];

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
