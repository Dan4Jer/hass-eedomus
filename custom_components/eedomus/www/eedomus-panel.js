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

const TABS = ['peripheriques', 'regles', 'historique'];
const TAB_LABELS = {
  peripheriques: 'Périphériques',
  regles: 'Règles',
  historique: 'Historique',
};

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
  }

  set hass(hass) {
    this._hass = hass;
    if (this._built) {
      this._loadPeripherals();
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
    if (this._hass) {
      this._loadPeripherals();
    }
  }

  disconnectedCallback() {
    window.removeEventListener('hashchange', this._boundHashChange);
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

        @media (max-width: 900px) {
          .periph-row {
            display: flex; flex-direction: column; align-items: stretch; gap: 8px;
          }
          .row-top { display: flex; align-items: center; gap: 8px; }
          .row-top .periph-identity { flex: 1; }
          .row-top .periph-meta { display: block; }
          .periph-mapping { border-top: 1px solid var(--divider-color); padding-top: 8px; }
          .row-action { width: 100%; }
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
        </nav>

        <main id="tab-content" aria-live="polite"></main>
      </div>
    `;

    this.shadowRoot.addEventListener('click', (ev) => this._onClick(ev));
    this.shadowRoot.addEventListener('input', (ev) => this._onInput(ev));
    this.shadowRoot.addEventListener('keydown', (ev) => this._onKeyDown(ev));

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
      } else {
        this._loadPeripherals();
      }
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

  _onInput(ev) {
    if (ev.target.id === 'periph-search') {
      this._search = ev.target.value;
      this._renderPeriphList();
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
      if (ev.target.id === 'periph-search') {
        if (ev.target.value !== '') {
          this._search = '';
          ev.target.value = '';
          this._renderPeriphList();
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
      <p class="result-count" id="periph-status" role="status"></p>
      <div class="periph-list" id="periph-list"></div>
    `;
  }

  _renderPeriphList() {
    const root = this.shadowRoot;
    if (!root || this._tab !== 'peripheriques') {
      return;
    }
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
    if (!list || !status) {
      return;
    }

    if (this._error) {
      status.textContent = '';
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
      status.textContent = '';
      list.innerHTML = '<div class="skeleton-row"></div>'.repeat(6);
      return;
    }

    if (this._periphs.length === 0) {
      status.textContent = '';
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

    const filterLabel = this._touchedOnly
      ? ` — filtre « Périphériques touchés » actif : ${rows.length} résultats`
      : '';
    status.textContent = `${this._periphs.length} périphériques${filterLabel}`;
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
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
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
    const text = editor.value;
    const lines = text.split('\n');
    gutter.textContent = lines.map((_, i) => i + 1).join('\n') + '\n';
    const esc = this._escapeHtml(text);
    // Coloration: comments first, then keys, then quoted strings, then
    // numbers/booleans - applied on the escaped text.
    let html = esc
      .replace(/(#.*)$/gm, '<span class="tok-comment">$1</span>')
      .replace(/^(\s*)([^#\n]+?)(:(\s|$))/gm,
        (match, indent, key, colon) =>
          `${indent}<span class="tok-key">${key}</span>${colon}`)
      .replace(/&quot;([^&]|&(?!quot;))*?&quot;|&#39;([^&]|&(?!#39;))*?&#39;/g,
        (match) => `<span class="tok-str">${match}</span>`)
      .replace(/\b(true|false|null)\b/g,
        '<span class="tok-bool">$1</span>')
      .replace(/(:\s|^)(-?\d+(\.\d+)?)(\s|$)/gm,
        (match, prefix, num, dec, suffix) =>
          `${prefix}<span class="tok-num">${num}</span>${suffix}`);
    pre.innerHTML = html;
    this._syncYamlScroll();
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
