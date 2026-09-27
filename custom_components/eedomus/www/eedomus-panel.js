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
    if (retry) {
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
    if (action) {
      this._createRuleFor(action.dataset.periphId, action.dataset.usageId);
    }
  }

  _onInput(ev) {
    if (ev.target.id === 'periph-search') {
      this._search = ev.target.value;
      this._renderPeriphList();
    }
  }

  _onKeyDown(ev) {
    if (ev.key === 'Escape' && ev.target.id === 'periph-search') {
      if (ev.target.value !== '') {
        this._search = '';
        ev.target.value = '';
        this._renderPeriphList();
      }
      ev.target.blur();
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
      const prefill = this._pendingRuleUsageId;
      content.innerHTML = `
        <p class="placeholder">
          L'éditeur de règles arrive au ticket suivant (formulaire structuré et
          mode YAML).${prefill ? ` usage_id pré-rempli prêt pour ce périphérique : <code>${this._escapeHtml(prefill)}</code>.` : ''}
        </p>
      `;
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
}

if (!customElements.get('eedomus-config-panel')) {
  customElements.define('eedomus-config-panel', EedomusConfigPanel);
}
