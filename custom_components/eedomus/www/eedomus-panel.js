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
      this._loadPeripherals();
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
    }
  }

  _onInput(ev) {
    if (ev.target.id === 'periph-search') {
      this._search = ev.target.value;
      this._renderPeriphList();
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
    } else {
      content.innerHTML = `
        <p class="placeholder">
          Aucune sauvegarde encore. La première sauvegarde archivera la version
          courante. (Les cartes de version et le diff arrivent au ticket
          Historique.)
        </p>
      `;
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

  async _saveRules() {
    const form = this._ruleForm;
    if (!form || !this._mapping) {
      return;
    }
    this._saveState = 'saving';
    this._updateRuleFormState();
    const mapping = JSON.parse(JSON.stringify(this._mapping));
    mapping.custom_usage_id_mappings = mapping.custom_usage_id_mappings || {};
    mapping.custom_usage_id_mappings[form.usage_id] = {
      ha_entity: form.ha_entity,
      ha_subtype: form.ha_subtype,
      justification: form.justification,
    };
    mapping.metadata = mapping.metadata || {};
    mapping.metadata.last_modified = new Date().toISOString().slice(0, 16).replace('T', ' ');
    try {
      await this._hass.callWS({
        type: 'eedomus/save_mapping',
        mapping,
      });
      this._saveState = 'applying';
      this._mapping = mapping;
      this._updateRuleFormState();
      // The save command reloads the entries: re-read the peripherals to
      // reflect the new mapping and produce the nominative feedback.
      await this._loadPeripherals();
      const rule = form.usage_id;
      const row = (this._periphs || []).find((p) => p.usage_id === rule);
      this._saveState = {
        applied: {
          entity_id: row && row.entity_id ? row.entity_id : `usage_id ${rule}`,
          unit: row && row.unit ? row.unit : 'sa nouvelle valeur',
        },
      };
      this._ruleForm = null;
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

    const rules = this._usageIdRules();
    const rulesListHtml = `
      <p class="result-count" id="rules-status" role="status"></p>
      <div class="periph-list" id="rules-list"></div>
    `;

    if (!this._ruleForm) {
      const prefillNote = this._pendingRuleUsageId
        ? `<p class="result-count">usage_id pré-rempli : <code>${this._escapeHtml(this._pendingRuleUsageId)}</code></p>`
        : '';
      return `
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

  _onRulesEvent(ev) {
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
