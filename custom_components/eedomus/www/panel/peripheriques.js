/**
 * Peripheriques tab of the Eedomus config panel (P.1.3).
 *
 * Real ES module imported by www/eedomus-panel.js: the tab's
 * stylesheet chunk and the peripheriques prototype mixin. Pure
 * extraction of the former single-file panel — the code moved as-is.
 */

import { periphStatusText } from './shared.js';

export const PERIPH_STYLES = `
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
`;

export function applyPeripheriquesMixin(EedomusConfigPanel) {
  Object.assign(EedomusConfigPanel.prototype, {
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
      // Raw message or the panel.* fallback key — the render resolves
      // it through t() (CAP-3).
      this._error = (err && (err.message || err.code)) ||
        'panel.common.command_refused';
    }
    this._loading = false;
    this._renderPeriphList();
  },

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
  },

  _renderPeriphToolbar() {
    const touchedCount = (this._periphs || []).filter((row) => row.modified).length;
    return `
      <div class="toolbar">
        <div class="search">
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M15.5 14h-.79l-.28-.27a6.5 6.5 0 1 0-.7.7l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0A4.5 4.5 0 1 1 14 9.5 4.5 4.5 0 0 1 9.5 14z"/></svg>
          <input id="periph-search" type="search"
                 placeholder="${this._escapeHtml(
                   this.t('panel.peripheriques.search.placeholder')
                 )}"
                 aria-label="${this._escapeHtml(
                   this.t('panel.peripheriques.search.aria')
                 )}"
                 value="${this._escapeHtml(this._search)}">
        </div>
        <button class="filter-touches" type="button"
                aria-pressed="${this._touchedOnly}">
          ${this.t('panel.peripheriques.filter.label')}
          <span class="count">
            ${this.t('panel.peripheriques.filter.count', { n: touchedCount })}
          </span>
        </button>
      </div>
      <p class="result-count" id="periph-status"></p>
      <p class="sr-only" id="periph-status-live" role="status"></p>
      <div class="periph-list" id="periph-list"></div>
    `;
  },

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
        countSpan.textContent = this.t('panel.peripheriques.filter.count', {
          n: touched,
        });
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
          ${this.t('panel.peripheriques.error.load', {
            err: this._escapeHtml(this.t(this._error)),
          })}
          <br>
          <button class="retry" type="button">${this.t('panel.common.retry')}</button>
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
          ${this.t('panel.peripheriques.empty')}
        </div>
      `;
      return;
    }

    const rows = this._filteredPeriphs();
    if (rows.length === 0 && this._search) {
      // Explicit search-no-result state (CAP-3 spine row) — never a
      // silent empty list. The count status keeps announcing.
      list.innerHTML = `
        <div class="state-message">
          ${this.t('panel.peripheriques.empty.search', {
            q: this._escapeHtml(this._search),
          })}
        </div>
      `;
      status.textContent = periphStatusText(
        this._periphs.length,
        rows.length,
        this._touchedOnly,
        this._t
      );
      if (announceStatus && live) {
        this._announceStatusNow(
          live,
          periphStatusText(
            this._periphs.length,
            rows.length,
            this._touchedOnly,
            this._t
          )
        );
      }
      return;
    }

    const parts = [];
    for (const row of rows) {
      parts.push(this._renderRow(row));
    }
    list.innerHTML = parts.join('');

    status.textContent = periphStatusText(
      this._periphs.length,
      rows.length,
      this._touchedOnly,
      this._t
    );
    if (announceStatus && live) {
      this._announceStatusNow(
        live,
        periphStatusText(
          this._periphs.length,
          rows.length,
          this._touchedOnly,
          this._t
        )
      );
    }
  },

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
      this._touchedOnly,
      this._t
    );
  },

  _renderRow(row) {
    const badge = row.modified
      ? `
        <span class="badge-modified"
              title="${this._escapeHtml(this.t('panel.peripheriques.badge.title', {
                rule: row.modified_by_rule,
                date: row.modified_date ||
                  this.t('panel.common.unknown_date'),
              }))}"
              aria-label="${this._escapeHtml(
                this.t('panel.peripheriques.badge.aria', {
                  rule: row.modified_by_rule,
                  date: row.modified_date ||
                    this.t('panel.common.unknown_date'),
                })
              )}">
          <span class="dot" aria-hidden="true"></span>
          <svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true"><path fill="currentColor" d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
          ${this.t('panel.peripheriques.badge.label')}
        </span>`
      : '<span></span>';

    const mappingMeta = [row.device_class, row.unit].filter(Boolean).join(' · ');
    return `
      <div class="periph-row">
        <div class="row-top">
          <div class="periph-identity">
            <span class="periph-name">${this._escapeHtml(row.name || row.periph_id)}</span>
            <span class="periph-meta">
              ${this.t('panel.peripheriques.row.usage_id_label')}
              <code>${this._escapeHtml(
                row.usage_id ||
                  this.t('panel.peripheriques.row.usage_id_missing')
              )}</code>
            </span>
          </div>
          ${badge}
        </div>
        <div class="periph-mapping">
          <span class="ha-entity">${
            row.entity_id
              ? this._escapeHtml(row.entity_id)
              : `<em>${this.t('panel.common.no_entity')}</em>`
          }</span>
          <span class="mapping-meta">${this._escapeHtml(mappingMeta || row.platform || '')}</span>
        </div>
        <button class="row-action" type="button"
                data-periph-id="${this._escapeAttr(row.periph_id)}"
                data-usage-id="${this._escapeAttr(row.usage_id || '')}">
          ${this.t('panel.peripheriques.row.create_rule')}
        </button>
      </div>
    `;
  },
  });
}
