/**
 * Historique tab of the Eedomus config panel (P.1.6).
 *
 * Real ES module imported by www/eedomus-panel.js: the tab's
 * stylesheet chunk and the history prototype mixin. Pure extraction
 * of the former single-file panel — the code moved as-is.
 */

export const HISTORY_STYLES = `
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
`;

export function applyHistoriqueMixin(EedomusConfigPanel) {
  Object.assign(EedomusConfigPanel.prototype, {
  // ================= Historique (P.1.6) =================

  async _loadVersions() {
    // In-flight guard (mirror of _loadCoherence): a hass reassignment
    // during the await must not duplicate the ws call and the render.
    if (!this._hass || this._versionsLoading) {
      return;
    }
    this._versionsLoading = true;
    this._versionsError = null;
    try {
      const result = await this._hass.callWS({
        type: 'eedomus/get_mapping_versions',
      });
      this._versions = (result && result.versions) || [];
      this._currentMapping = (result && result.current) || {};
    } catch (err) {
      this._versionsError = (err && (err.message || err.code)) ||
        'panel.common.command_refused';
    }
    this._versionsLoading = false;
    if (this._tab === 'historique') {
      const content = this.shadowRoot.getElementById('tab-content');
      if (content) {
        content.innerHTML = this._renderHistoryTab();
        this._wireHistoryTab();
      }
    }
  },

  _formatTimestamp(ts) {
    if (!ts) {
      return 'panel.common.unknown_date';
    }
    // Storage format: 2026-09-28T09:19:00
    const [datePart, timePart] = String(ts).split('T');
    if (!timePart) {
      return datePart;
    }
    return `${datePart} ${timePart.slice(0, 5)}`;
  },

  _reasonLabel(reason) {
    if (reason === 'ingestion') {
      return 'panel.historique.reason.ingestion';
    }
    if (reason === 'migration') {
      return 'panel.historique.reason.migration';
    }
    return 'panel.historique.reason.panel';
  },

  _renderHistoryTab() {
    if (this._versionsError) {
      return `
        <div class="state-message" role="alert">
          ${this.t('panel.historique.error.load', {
            err: this._escapeHtml(this.t(this._versionsError)),
          })}
          <br>
          <button class="retry" type="button" data-retry="versions">
            ${this.t('panel.common.retry')}
          </button>
        </div>
      `;
    }
    if (this._versions === null) {
      return '<div class="skeleton-row"></div>'.repeat(3);
    }
    if (this._versions.length === 0) {
      return `
        <div class="state-message">
          ${this.t('panel.historique.empty')}
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
          <span class="version-title">
            ${this.t('panel.historique.current.title')}
          </span>
          <span class="version-active">
            ${this.t('panel.historique.current.badge')}
          </span>
          <span class="version-meta">
            ${this.t('panel.historique.current.meta')}
          </span>
        </div>
      </div>
    `);
    // Archived versions, newest first, max three
    this._versions.slice(0, 3).forEach((version, index) => {
      const confirm = this._confirmRestore === index;
      const diffHtml =
        this._versions.length === 1
          ? `<p class="version-meta">${this.t(
              'panel.historique.diff.first_version'
            )}</p>`
          : this._renderDiff(index);
      cards.push(`
        <div class="version-card">
          <div class="version-head">
            <span class="version-title">${this.t(
              'panel.historique.version.title',
              {
                timestamp: this._escapeHtml(
                  this.t(this._formatTimestamp(version.timestamp))
                ),
              }
            )}</span>
            <span class="version-meta">${this._escapeHtml(
              this.t(this._reasonLabel(version.reason))
            )}</span>
            <button class="row-action" type="button" data-restore="${index}">
              ${confirm
                ? this.t('panel.historique.restore.confirm')
                : this.t('panel.historique.restore.action')}
            </button>
          </div>
          ${confirm
            ? `<p class="form-validation" role="alert">${this.t(
                'panel.historique.restore.confirm_message',
                {
                  ts: this._escapeHtml(
                    this.t(this._formatTimestamp(version.timestamp))
                  ),
                }
              )}</p>`
            : ''}
          ${diffHtml}
        </div>
      `);
    });

    return `${statusHtml}<div class="versions">${cards.join('')}</div>`;
  },

  _wireHistoryTab() {
    const status = this.shadowRoot.getElementById('history-status');
    if (status) {
      status.textContent = this._historyStatusText();
    }
  },

  // Restore status as a key descriptor resolved at display time — a
  // mid-session locale switch never replays a stale-language status
  // (same key-storing model as _error/_validation/_yamlError).
  _historyStatusText() {
    const status = this._historyStatus;
    if (!status) {
      return '';
    }
    return this.t(
      status.key,
      status.ts != null ? { ts: this.t(status.ts) } : null
    );
  },

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
        const lineKey = op.type === 'added'
          ? 'panel.historique.diff.line_added'
          : op.type === 'removed'
            ? 'panel.historique.diff.line_removed'
            : 'panel.historique.diff.line_modified';
        return `<div class="diff-line ${cls}"` +
          ` aria-label="${this._escapeHtml(this.t(lineKey))}">` +
          `<span class="prefix" aria-hidden="true">${prefix}</span>` +
          `<span class="content">${this._escapeHtml(op.line)}</span></div>`;
      })
      .join('');
    return `<div class="diff" tabindex="0" role="region"` +
      ` aria-label="${this._escapeHtml(
        this.t('panel.historique.diff.region_aria')
      )}">${html}</div>`;
  },

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
  },

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
    this._historyStatus = { key: 'panel.historique.restore.progress' };
    const content = this.shadowRoot.getElementById('tab-content');
    if (content) {
      content.innerHTML = this._renderHistoryTab();
      this._wireHistoryTab();
    }
    const ok = await this._persistMapping(version.config || {});
    if (ok) {
      this._historyStatus = {
        key: 'panel.historique.restore.success',
        ts: this._formatTimestamp(version.timestamp),
      };
      this._versions = null;
      await this._loadVersions();
    } else {
      this._historyStatus = { key: 'panel.historique.restore.failed' };
    }
    const status = this.shadowRoot.getElementById('history-status');
    if (status) {
      status.textContent = this._historyStatusText();
    }
  },
  });
}
