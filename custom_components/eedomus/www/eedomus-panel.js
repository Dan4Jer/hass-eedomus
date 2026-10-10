/**
 * Eedomus Config panel — ES-module entry, served at
 * /local/eedomus/eedomus-panel.js (the URL panel.py registers).
 *
 * The panel is split across real ES modules (story 102): this entry
 * keeps the core — constructor and state, the t() catalog loading,
 * lifecycle, tab/hash navigation, the _render shell (base styles
 * plus the composed per-tab *_STYLES chunks) and the event
 * delegation — then calls customElements.define. Every module
 * contributes its class methods through a prototype mixin and its
 * tab carries its stylesheet chunk:
 *   ./panel/shared.js        — transverse constants and helpers,
 *                              announce/escape/cache mixin
 *   ./panel/coherence.js     — coherence pure helpers, mixin, styles
 *   ./panel/peripheriques.js — peripheriques mixin and styles
 *   ./panel/regles.js        — rules form/YAML mixin and styles
 *   ./panel/historique.js    — mapping versions mixin and styles
 *   ./panel/supervision.js    — box metrics mixin and styles
 *
 * Theming: HA CSS variables only (no hard-coded style). The panel is
 * keyboard-operable and announces state changes through aria-live.
 */

import {
  TABS,
  COPY_WRITE_TIMEOUT_MS,
  STRINGS_LOAD_TIMEOUT_MS,
  applySharedMixin,
  menuButtonHtml,
  MENU_BUTTON_STYLES,
} from './panel/shared.js';
import {
  applyCoherenceMixin,
  COHERENCE_STYLES,
  coherenceNarrowMedia,
  coherenceNarrowView,
  coherenceExpandedRowId,
} from './panel/coherence.js';
import { applyPeripheriquesMixin, PERIPH_STYLES } from './panel/peripheriques.js';
import { applyReglesMixin, RULES_STYLES } from './panel/regles.js';
import { applyHistoriqueMixin, HISTORY_STYLES } from './panel/historique.js';
import { applySupervisionMixin, SUPERVISION_STYLES } from './panel/supervision.js';

class EedomusConfigPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._hass = null;
    // i18n catalog (CAP-3): (locale, strings) from
    // eedomus/get_translations. Absent until the command answers —
    // renders then stay on skeletons, never a key as text.
    this._strings = null;
    this._stringsLocale = null;
    this._stringsLoadingLocale = null;
    // Generation token (i18n retro fix-now): each _loadStrings call
    // bumps it; a continuation whose generation was superseded neither
    // frees the slot nor writes the catalog — value-identical locales
    // (fr, flip away, flip back) would otherwise collide.
    this._stringsLoadGeneration = 0;
    // Translator handed to the pure helpers (they stay this-free).
    this._t = (key, params) => this.t(key, params);
    this._config = {};
    this._tab = 'supervision';
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
    this._mappingLoading = false; // in-flight guard (deep-link restarts)
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
    this._versionsLoading = false; // in-flight guard (deep-link restarts)
    this._confirmRestore = null;
    this._historyStatus = null; // null | {key, ts?} — resolved via t()
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
    // Cache generation (sweep): a load started before a write must not
    // repopulate the cache the write invalidated — its resolution is
    // discarded when the generation moved (same discard pattern as the
    // stale-locale guard of _loadStrings).
    this._coherenceGeneration = 0;
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
    // Supervision tab state (ticket 4.2) — one callWS per tab visit,
    // no subscription, no polling (same contract as the other lazy
    // tabs). Generation discards superseded in-flight resolutions.
    this._metrics = null;
    this._metricsError = null;
    this._metricsErrorDetail = null;
    this._metricsLoading = false;
    this._metricsGeneration = 0;
    // Backfill queue state (ticket 4.3) — the tab's second parallel
    // load, with its own error/skeleton slot (the two zones resolve
    // independently). The last refused action and the pending ignore
    // confirmation are volatile per visit.
    this._backfill = null;
    this._backfillError = null;
    this._backfillErrorDetail = null;
    this._backfillLoading = false;
    this._backfillGeneration = 0;
    // One backfill action at a time (in-flight guard), generations
    // dropping superseded resolutions — mirror of the load slots.
    this._backfillActionLoading = false;
    this._backfillActionGen = 0;
    this._backfillActionError = null;
    this._confirmIgnore = null;
    this._boundCoherenceBreakpoint = (ev) => this._onCoherenceBreakpoint(ev);
  }

  set hass(hass) {
    this._hass = hass;
    this._loadStrings();
    if (this._built) {
      this._loadPeripherals();
      // Direct deep-link entry into a lazy tab: the tab rendered
      // before hass was assigned, so its lazy load bailed out —
      // start it now. One branch per lazy tab, same guards as
      // _renderTabContent (closes #regles and bug 105 #historique).
      if (this._tab === 'regles' && this._mapping === null
          && !this._mappingError) {
        this._loadMapping();
      } else if (this._tab === 'historique' && this._versions === null
          && !this._versionsError) {
        this._loadVersions();
      } else if (this._tab === 'coherence' && this._coherence === null
          && !this._coherenceError) {
        this._loadCoherence();
      } else if (this._tab === 'supervision') {
        // Two parallel loads, independent slots: a deep-link entry
        // starts both (the zones resolve on their own).
        if (this._metrics === null && !this._metricsError) {
          this._loadMetrics();
        }
        if (this._backfill === null && !this._backfillError) {
          this._loadBackfill();
        }
      }
    }
  }

  get hass() {
    return this._hass;
  }

  // Translator (CAP-3): the catalog text with {token} params replaced.
  // A missing key returns the key itself (developer-visible); an absent
  // catalog also returns keys — renders gate on the catalog so users
  // never see them. Simple replacement, no escaping here: values are
  // escaped where the surrounding templates already escape them.
  t(key, params) {
    const text = (this._strings && this._strings[key]) || key;
    if (!params) {
      return text;
    }
    return text.replace(/\{(\w+)\}/g, (match, name) =>
      params[name] === undefined || params[name] === null
        ? match
        : String(params[name])
    );
  }

  // Catalog loading (CAP-3): one request per locale, fired from set
  // hass. A failure leaves the panel without a catalog (skeletons) —
  // the next set hass retries naturally; a locale change reloads.
  async _loadStrings() {
    const hass = this._hass;
    if (!hass || !hass.callWS) {
      return;
    }
    const locale = (hass.locale && hass.locale.language) || 'en';
    if (this._stringsLoadingLocale === locale) {
      return;
    }
    if (this._strings && this._stringsLocale === locale) {
      return;
    }
    this._stringsLoadingLocale = locale;
    const generation = ++this._stringsLoadGeneration;
    let translations = null;
    let timeoutId = null;
    try {
      // Race: a dropped websocket (connection lost mid-flight) never
      // settles — the timeout resolves the race, the slot frees, and
      // the next set hass retries naturally.
      const wsCall = hass.callWS({
        type: 'eedomus/get_translations',
        locale,
      });
      // A rejection arriving after the timeout has won the race must
      // not surface as an unhandled rejection: the slot is already
      // freed, the error is dead.
      wsCall.catch(() => {});
      const result = await Promise.race([
        wsCall,
        new Promise((resolve) => {
          timeoutId = setTimeout(() => resolve(null),
            STRINGS_LOAD_TIMEOUT_MS);
        }),
      ]);
      translations = (result && result.translations) || null;
    } catch (err) {
      translations = null;
    } finally {
      if (timeoutId !== null) {
        clearTimeout(timeoutId);
      }
    }
    if (generation !== this._stringsLoadGeneration) {
      // A newer call superseded this one (locale flip and back, or a
      // retry after this call's timeout freed the slot): the loading
      // marker and the catalog belong to the newer call — a late
      // continuation must not erase an in-flight marker.
      return;
    }
    this._stringsLoadingLocale = null;
    const current = (this._hass && this._hass.locale &&
      this._hass.locale.language) || 'en';
    if (!translations || locale !== current) {
      // Failure or stale response (the locale changed mid-flight):
      // no catalog, skeletons — the next set hass retries.
      return;
    }
    this._strings = translations;
    this._stringsLocale = locale;
    if (this._built) {
      this._render();
    }
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
    return TABS.includes(hash) ? hash : 'supervision';
  }

  _onHashChange() {
    // Back/forward between tabs: the URL hash is the source of truth.
    const tab = this._tabFromLocation();
    if (tab !== this._tab) {
      if (this._tab === 'supervision') {
        // Back/forward leaves the tab: the pending ignore
        // confirmation voids, same as _setTab.
        this._confirmIgnore = null;
      }
      this._tab = tab;
      // The replaced table carries no anchor row: like the popover,
      // a stale expanded row never survives the switch.
      this._coherenceExpandedId = null;
      this._renderTabContent();
    }
  }

  _setTab(tab, updateHash = true) {
    if (tab !== this._tab && this._tab === 'supervision') {
      // Leaving the Supervision tab voids the pending ignore
      // confirmation (volatile per visit, ticket 4.3).
      this._confirmIgnore = null;
    }
    this._tab = tab;
    if (updateHash) {
      window.location.hash = tab;
    }
    this._renderTabContent();
  }

  _render() {
    if (!this.shadowRoot) {
      return;
    }
    // Listeners live on the shadow root itself: attached once, on the
    // first build — a catalog re-render never doubles them.
    if (!this._built) {
      this._built = true;
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
    }
    if (!this._strings) {
      // Catalog absent (in flight or failed): skeletons only — no text
      // at all, never a key shown to the user. The next set hass
      // retries the command and re-renders.
      this.shadowRoot.innerHTML = `
        <style>
          .skeleton-row {
            height: 64px;
            background: var(--card-background-color);
            border: 1px solid var(--divider-color);
            border-radius: var(--ha-card-border-radius, 12px);
            opacity: 0.6;
          }
        </style>
        <div class="panel" role="status" aria-busy="true">
          <div class="skeleton-row"></div>
          <div class="skeleton-row"></div>
          <div class="skeleton-row"></div>
        </div>`;
      return;
    }
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

        .tabs { display: flex; flex-wrap: wrap; gap: 8px; padding: 12px 0 20px; }
${MENU_BUTTON_STYLES}
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
${PERIPH_STYLES}

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
${RULES_STYLES}
${HISTORY_STYLES}
${COHERENCE_STYLES}
${SUPERVISION_STYLES}
      </style>

      <div class="panel">
        ${menuButtonHtml(this._t)}
        <header class="panel-header">
          <h1>${this.t('panel.common.title')}</h1>
        </header>

        <nav class="tabs" aria-label="${this._escapeHtml(
          this.t('panel.nav.aria')
        )}">
          <button class="tab" role="tab" data-tab="supervision"
                  aria-selected="false">${this.t('panel.tabs.supervision')}</button>
          <button class="tab" role="tab" data-tab="peripheriques"
                  aria-selected="false">${this.t('panel.tabs.peripheriques')}</button>
          <button class="tab" role="tab" data-tab="regles"
                  aria-selected="false">${this.t('panel.tabs.regles')}</button>
          <button class="tab" role="tab" data-tab="historique"
                  aria-selected="false">${this.t('panel.tabs.historique')}</button>
          <button class="tab" role="tab" data-tab="coherence"
                  aria-selected="false">${this.t('panel.tabs.coherence')}</button>
        </nav>

        <main id="tab-content" aria-live="polite"></main>
        <p class="sr-only" id="backfill-status-live" role="status"></p>
      </div>
    `;

    this._renderTabContent();
  }

  _onClick(ev) {
    const menu = ev.target.closest('[data-action="toggle-menu"]');
    if (menu) {
      // Issue #125 / ticket 116: custom panels get no HA app-header,
      // so on narrow viewports this button is the only way out. It
      // opens HA's drawer through the standard ha-menu-button event —
      // no proprietary navigation.
      this.dispatchEvent(
        new Event('hass-toggle-menu', { bubbles: true, composed: true })
      );
      return;
    }
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
      } else if (retry.dataset.retry === 'backfill') {
        this._backfillError = null;
        this._backfillErrorDetail = null;
        this._loadBackfill();
      } else if (retry.dataset.retry === 'metrics') {
        this._metricsError = null;
        this._metricsErrorDetail = null;
        this._loadMetrics();
      } else {
        this._loadPeripherals();
      }
      return;
    }
    const gotoCoherence = ev.target.closest('[data-goto-coherence]');
    if (gotoCoherence) {
      // Supervision's internal link: same mechanism as the "create a
      // rule" shortcut — the tab switch flows through _setTab so the
      // hash and back/forward keep working.
      this._setTab('coherence');
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
      // Focus contract (mirror of _coherenceSortBy): the re-render
      // replaces the coherence body, removing the "Show all" button
      // with its empty state — the keyboard user lands on the view
      // toggle, the control that owns the state.
      const viewBtn = this.shadowRoot.querySelector('[data-coherence-view]');
      if (viewBtn) {
        viewBtn.focus();
      }
      return;
    }
    const popoverTrigger = ev.target.closest('[data-coherence-popover]');
    if (popoverTrigger) {
      this._cancelCoherenceHover();
      if (coherenceNarrowView()) {
        // Under 900 px (2.5): a tap expands the row — the 2.4
        // popover stays a desktop surface, the hover gating is intact.
        this._toggleCoherenceExpanded(
          popoverTrigger.dataset.coherencePopover
        );
        return;
      }
      // Enter/click on the periph_id cell: open without the hover
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
      // CAP-8: the entity link navigates to the standard HA surface —
      // never the popover or the extension (stopPropagation), and the
      // fallback href="#" never touches the panel hash.
      ev.preventDefault();
      ev.stopPropagation();
      this._openEntityMoreInfo(entityLink.dataset.entityId);
      return;
    }
    const copyJsonBtn = ev.target.closest('[data-copy-json]');
    if (copyJsonBtn) {
      // Copy stays on its surface: no popover/extension teardown, the
      // verdict lands in the dedicated copy-status-live region.
      this._copyCoherenceRawJson(copyJsonBtn);
      return;
    }
    const filterBtn = ev.target.closest('.filter-touches');
    if (filterBtn) {
      this._touchedOnly = !this._touchedOnly;
      this._renderPeriphList();
      return;
    }
    if (this._tab === 'supervision') {
      // Supervision's own delegation runs BEFORE the generic
      // .row-action + periphId branch below: the queue rows use
      // .row-action buttons too, and the generic branch would route
      // them to _createRuleFor (collision).
      this._onSupervisionEvent(ev);
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
    // Middle-click / "open in a new tab" on the fallback
    // href="#": the entity link never navigates by itself —
    // only the standard HA surface (hass-more-info) opens, and the
    // panel hash stays intact.
    if (ev.target.closest && ev.target.closest('[data-entity-id]')) {
      ev.preventDefault();
    }
  }

  // Copy of the payload JSON (UX run 3): the text comes from the
  // rendered <code> of the open detail — textContent unescapes, so
  // the clipboard receives the exact rendered payload, no re-fetch.
  // The clipboard API first (raced against a short timeout — a stuck
  // permission prompt never settles), then an execCommand fallback
  // (insecure context, refused permission); the verdict is always
  // announced in the dedicated copy-status-live region — a copy
  // failure is never silent.
  async _copyCoherenceRawJson(btn) {
    const details = btn.closest ? btn.closest('details') : null;
    const code = details ? details.querySelector('.raw-json code') : null;
    const text = code ? code.textContent : '';
    const root = this.shadowRoot;
    const live = root ? root.getElementById('copy-status-live') : null;
    const announce = (copied) => {
      if (live) {
        this._announceStatusNow(
          live,
          this.t(
            copied
              ? 'panel.coherence.detail.copy_feedback'
              : 'panel.coherence.detail.copy_failed'
          )
        );
      }
    };
    // Missing markup or an empty payload copies nothing — announce
    // the failure, never attempt a copy of the empty string.
    if (!code || !text) {
      announce(false);
      return;
    }
    const clipboard =
      typeof navigator !== 'undefined' && navigator.clipboard
        ? navigator.clipboard
        : null;
    let copied = false;
    if (clipboard && clipboard.writeText) {
      try {
        copied = await Promise.race([
          clipboard.writeText(text).then(() => true),
          new Promise((resolve) => {
            setTimeout(() => resolve(false), COPY_WRITE_TIMEOUT_MS);
          }),
        ]);
      } catch (err) {
        copied = false;
      }
    }
    if (!copied) {
      copied = this._copyCoherenceRawFallback(text);
    }
    announce(copied);
  }

  // execCommand fallback of the JSON copy: an off-viewport textarea,
  // select then copy, cleanup — the honest boolean verdict decides
  // the announcement.
  _copyCoherenceRawFallback(text) {
    if (
      typeof document === 'undefined' ||
      !document.createElement ||
      !document.execCommand
    ) {
      return false;
    }
    const area = document.createElement('textarea');
    area.value = text;
    area.setAttribute('readonly', '');
    area.style.position = 'fixed';
    area.style.top = '-9999px';
    document.body.appendChild(area);
    // execCommand('copy') reads the selection of the focused element
    // in several browsers — focus before select.
    area.focus();
    area.select();
    let copied = false;
    try {
      copied = document.execCommand('copy');
    } catch (err) {
      copied = false;
    }
    document.body.removeChild(area);
    return copied;
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
        // Escape closes the popover (the popover already intercepts
        // Escape when it holds the focus — this branch is the net for
        // a popover opened on hover, never focused). Without the
        // focus inside, Escape continues to the active field: clearing
        // the search must keep working.
        const pop = this._coherencePopover;
        const active = this.shadowRoot.activeElement;
        this._closeCoherencePopover();
        if (pop.contains(active)) {
          return;
        }
      }
      if (this._coherenceExpandedId !== null) {
        // Escape also closes the mobile expanded row (same gesture as
        // the popover, 2.5): the focus returns to the trigger when it
        // operated the extension; otherwise Escape continues to the
        // active field — clearing the search stays functional (2.4
        // contract).
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
    // Shortcut: switch to Rules with the usage_id pre-filled (P.1.4
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
    } else if (this._tab === 'supervision') {
      content.innerHTML = this._renderSupervisionTab();
      if (this._metrics === null && !this._metricsError) {
        this._loadMetrics();
      }
      if (this._backfill === null && !this._backfillError) {
        this._loadBackfill();
      }
    } else {
      content.innerHTML = `
        <p class="placeholder">
          ${this.t('panel.common.unknown_tab')}
        </p>
      `;
    }
  }
}

// The tab modules contribute their class methods through the mixins;
// the entry keeps the core, shell, styles composition and delegation.
applySharedMixin(EedomusConfigPanel);
applyCoherenceMixin(EedomusConfigPanel);
applyPeripheriquesMixin(EedomusConfigPanel);
applyReglesMixin(EedomusConfigPanel);
applyHistoriqueMixin(EedomusConfigPanel);
applySupervisionMixin(EedomusConfigPanel);

if (!customElements.get('eedomus-config-panel')) {
  customElements.define('eedomus-config-panel', EedomusConfigPanel);
}
