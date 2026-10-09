/**
 * Regles tab of the Eedomus config panel (P.1.4/P.1.5).
 *
 * Real ES module imported by www/eedomus-panel.js: the tab's
 * stylesheet chunk and the rules/YAML prototype mixin. Pure
 * extraction of the former single-file panel — the code moved as-is.
 */

export const RULES_STYLES = `
        .rules-help {
          margin: 0 0 12px;
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 12px);
          padding: 6px 12px;
          background: var(--card-background-color);
        }
        .rules-help summary { cursor: pointer; font-size: 13px; }
        .rules-help p {
          margin: 8px 0 0; font-size: 13px;
          color: var(--secondary-text-color);
        }
        .rules-help-example {
          margin: 8px 0 0; padding: 8px 10px; font-size: 12.5px;
          background: var(--secondary-background-color, inherit);
          border-radius: 8px; overflow-x: auto;
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
`;

export function applyReglesMixin(EedomusConfigPanel) {
  Object.assign(EedomusConfigPanel.prototype, {
  // ================= Rules (P.1.4) =================

  async _loadMapping() {
    // In-flight guard (mirror of _loadCoherence): a hass reassignment
    // during the await must not duplicate the ws call and the render.
    if (!this._hass || this._mappingLoading) {
      return;
    }
    this._mappingLoading = true;
    this._mappingError = null;
    try {
      const result = await this._hass.callWS({
        type: 'eedomus/get_mapping',
      });
      this._mapping = (result && result.mapping) || {};
    } catch (err) {
      this._mappingError = (err && (err.message || err.code)) ||
        'panel.common.command_refused';
    }
    this._mappingLoading = false;
    if (this._tab === 'regles') {
      const content = this.shadowRoot.getElementById('tab-content');
      if (content) {
        content.innerHTML = this._renderRulesTab();
        this._wireRulesTab();
      }
    }
  },

  _usageIdRules() {
    const mappings = (this._mapping && this._mapping.custom_usage_id_mappings) || {};
    return Object.entries(mappings)
      .map(([usageId, rule]) => ({ usageId, rule }))
      .sort((a, b) => a.usageId.localeCompare(b.usageId, undefined, { numeric: true }));
  },

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
  },

  _scheduleValidation() {
    if (this._validateTimer) {
      clearTimeout(this._validateTimer);
    }
    this._validateTimer = setTimeout(() => this._validateRuleForm(), 350);
  },

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
          message: (error && (error.message || error.error)) ||
            'panel.regles.validation.invalid',
        };
      }
    } catch (err) {
      this._validation = {
        valid: false,
        message: (err && (err.message || err.code)) ||
          'panel.regles.validation.unavailable',
      };
    }
    if (this._tab === 'regles' && this._ruleForm) {
      this._updateRuleFormState();
    }
  },

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
        : this.t(this._validation.message);
    }
    if (saveBtn) {
      const clientValid = form.usage_id && form.justification.trim() !== '';
      saveBtn.disabled = !(clientValid && this._validation.valid) ||
        this._saveState === 'saving' ||
        this._saveState === 'applying';
      saveBtn.textContent =
        this._saveState === 'saving'
          ? this.t('panel.common.saving')
          : this._saveState === 'applying'
            ? this.t('panel.common.applying')
            : this.t('panel.common.save');
    }
    this._updateRulesStatus();
  },

  _updateRulesStatus() {
    const status = this.shadowRoot.getElementById('rules-status');
    if (!status) {
      return;
    }
    if (this._saveState === 'saving') {
      status.textContent = this.t('panel.common.saving');
    } else if (this._saveState === 'applying') {
      status.textContent = this.t('panel.common.applying');
    } else if (this._saveState && this._saveState.applied === true) {
      status.textContent = this.t('panel.regles.status.applied');
    } else if (this._saveState && this._saveState.applied) {
      const applied = this._saveState.applied;
      // Fallback descriptors resolve through t() at display time — a
      // mid-session locale switch never replays a stale language.
      const resolveApplied = (value) =>
        value && typeof value === 'object'
          ? this.t(value.key, value.params)
          : value;
      status.textContent = this.t('panel.regles.status.rule_applied', {
        entity: resolveApplied(applied.entity_id),
        unit: resolveApplied(applied.unit),
      });
    } else if (this._saveState && this._saveState.error) {
      status.textContent = this.t('panel.regles.status.save_failed', {
        err: this.t(this._saveState.error),
      });
    } else if (this._validation.message) {
      status.textContent = this.t(this._validation.message);
    } else {
      status.textContent = this._rulesStatus;
    }
  },

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
      // Invalidated immediately after the write succeeds: a failure
      // of the subsequent peripherals reload must not skip it (the
      // mapping on the box already changed).
      this._invalidateCoherenceCache();
      this._updateYamlState();
      this._updateRuleFormState();
      await this._loadPeripherals();
      this._saveState = { applied: true };
      return true;
    } catch (err) {
      this._saveState = {
        error: (err && (err.message || err.code)) ||
          'panel.common.unknown_error',
      };
      return false;
    }
  },

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
          entity_id: row && row.entity_id
            ? row.entity_id
            : {
                key: 'panel.regles.status.rule_applied_entity_fallback',
                params: { rule },
              },
          unit: row && row.unit
            ? row.unit
            : { key: 'panel.regles.status.rule_applied_unit_fallback' },
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
  },

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
      // Invalidated immediately after the write succeeds: a failure
      // of the subsequent peripherals reload must not skip it (the
      // mapping on the box already changed).
      this._invalidateCoherenceCache();
      this._saveState = {
        applied: {
          entity_id: {
            key: 'panel.regles.status.deleted_entity',
            params: { usageId },
          },
          unit: { key: 'panel.regles.status.deleted_unit' },
        },
      };
      await this._loadPeripherals();
    } catch (err) {
      this._saveState = {
        error: (err && (err.message || err.code)) ||
          'panel.common.unknown_error',
      };
    }
    const content = this.shadowRoot.getElementById('tab-content');
    if (content && this._tab === 'regles') {
      content.innerHTML = this._renderRulesTab();
      this._wireRulesTab();
    }
    this._updateRulesStatus();
  },

  _renderRulesList() {
    const listEl = this.shadowRoot.getElementById('rules-list');
    if (!listEl) {
      return;
    }
    const rules = this._usageIdRules();
    if (rules.length === 0) {
      listEl.innerHTML = `
        <div class="state-message">
          ${this.t('panel.regles.empty')}
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
              <span class="periph-name">
                ${this.t('panel.regles.row.usage_id_label')}
                <code>${this._escapeHtml(usageId)}</code>
              </span>
              <span class="periph-meta">${this._escapeHtml(rule.justification || '')}</span>
            </div>
          </div>
          <div class="periph-mapping">
            <span class="ha-entity">${this._escapeHtml(rule.ha_entity || '')}${rule.ha_subtype ? '.' + this._escapeHtml(rule.ha_subtype) : ''}</span>
          </div>
          <button class="row-action" type="button" data-edit-rule="${this._escapeAttr(usageId)}">
            ${this.t('panel.regles.row.edit')}
          </button>
          <button class="row-action" type="button" data-delete-rule="${this._escapeAttr(usageId)}">
            ${confirm
              ? this.t('panel.regles.row.delete_confirm')
              : this.t('panel.regles.row.delete')}
          </button>
        </div>
      `;
      })
      .join('');
  },

  _rulesHelpHtml() {
    // CAP-10 (story 107): a collapsed grammar summary, present in
    // both edit modes; the full format lives in the repo doc page.
    const docUrl = (
      'https://github.com/Dan4Jer/hass-eedomus/blob/main/' +
      'docs/mapping-format.md'
    );
    return `
      <details class="rules-help">
        <summary>${this._escapeHtml(
          this.t('panel.regles.help.summary')
        )}</summary>
        <p>${this._escapeHtml(this.t('panel.regles.help.intro'))}</p>
        <pre class="rules-help-example"><code>custom_usage_id_mappings:
  "7":
    ha_entity: sensor
    ha_subtype: temperature
    device_class: temperature
    justification: Temperature sensor - usage 7</code></pre>
        <p><a href="${docUrl}" target="_blank" rel="noopener">
          ${this._escapeHtml(this.t('panel.regles.help.doc_link'))}
        </a></p>
      </details>
    `;
  },

  _renderRulesTab() {
    if (this._mappingError) {
      return `
        <div class="state-message" role="alert">
          ${this.t('panel.regles.error.load', {
            err: this._escapeHtml(this.t(this._mappingError)),
          })}
          <br>
          <button class="retry" type="button" data-retry="mapping">
            ${this.t('panel.common.retry')}
          </button>
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
      <div class="mode-toggle" role="group"
           aria-label="${this._escapeHtml(this.t('panel.regles.mode.aria'))}">
        <button type="button" data-rule-mode="form"
                aria-pressed="${this._rulesMode === 'form'}">
          ${this.t('panel.regles.mode.form')}
        </button>
        <button type="button" data-rule-mode="yaml"
                aria-pressed="${this._rulesMode === 'yaml'}">
          ${this.t('panel.regles.mode.yaml')}
        </button>
      </div>
      ${this._rulesHelpHtml()}
    `;

    if (this._rulesMode === 'yaml') {
      return `
        ${modeToggle}
        <div class="yaml-editor-wrap">
          <div class="yaml-gutter" id="yaml-gutter" aria-hidden="true"></div>
          <div class="yaml-code-area">
            <pre class="yaml-highlight" id="yaml-highlight" aria-hidden="true"></pre>
            <textarea class="yaml-editor" id="yaml-editor" spellcheck="false"
              aria-label="${this._escapeHtml(this.t('panel.regles.yaml.aria'))}"
              aria-describedby="yaml-error"></textarea>
          </div>
        </div>
        <p class="form-validation" id="yaml-error" role="alert">${
          this._yamlError
            ? this._escapeHtml(this.t(this._yamlError.message))
            : ''
        }</p>
        <div class="form-actions">
          <button class="row-action" id="yaml-save" type="button" disabled>
            ${this.t('panel.common.save')}
          </button>
        </div>
        <p class="result-count" id="rules-status" role="status"></p>
      `;
    }

    if (!this._ruleForm) {
      const prefillNote = this._pendingRuleUsageId
        ? `<p class="result-count">${this.t('panel.regles.prefill_note', {
            id: `<code>${this._escapeHtml(this._pendingRuleUsageId)}</code>`,
          })}</p>`
        : '';
      return `
        ${modeToggle}
        ${prefillNote}
        <div class="toolbar">
          <button class="row-action" type="button" data-new-rule="${this._escapeAttr(this._pendingRuleUsageId || '')}">
            ${this.t('panel.regles.create_rule')}
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
      ${this._rulesHelpHtml()}
      <form class="rule-form" id="rule-form" novalidate>
        <div class="form-field">
          <label for="rule-usage-id">
            ${this.t('panel.regles.form.usage_id')}
          </label>
          <input id="rule-usage-id" list="${datalistId}" type="text" inputmode="numeric"
                 placeholder="${this._escapeHtml(
                   this.t('panel.regles.form.usage_id_placeholder')
                 )}"
                 required
                 aria-describedby="rule-validation"
                 value="${this._escapeAttr(form.usage_id)}">
          <datalist id="${datalistId}">${options}</datalist>
        </div>
        <div class="form-field">
          <label for="rule-name">${this.t('panel.regles.form.name')}</label>
          <input id="rule-name" type="text"
                 placeholder="${this._escapeHtml(
                   this.t('panel.regles.form.name_placeholder')
                 )}"
                 required aria-describedby="rule-validation"
                 value="${this._escapeAttr(form.justification)}">
        </div>
        <div class="form-field">
          <label for="rule-entity">
            ${this.t('panel.regles.form.ha_entity')}
          </label>
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
          <label for="rule-subtype">
            ${this.t('panel.regles.form.ha_subtype')}
          </label>
          <select id="rule-subtype">
            <option value=""${
              form.ha_subtype === '' ? ' selected' : ''
            }>${this.t('panel.regles.form.ha_subtype_none')}</option>
            ${['temperature', 'humidity', 'energy', 'power', 'time', 'cpu', 'disk_free_space', 'text']
              .map(
                (subtype) =>
                  `<option value="${subtype}"${form.ha_subtype === subtype ? ' selected' : ''}>${subtype}</option>`
              )
              .join('')}
          </select>
          <span class="form-hint">
            ${this.t('panel.regles.form.ha_subtype_hint')}
          </span>
        </div>
        <p id="rule-validation" class="form-validation" role="alert"></p>
        <div class="form-actions">
          <button class="row-action" type="button" data-cancel-rule="1">
            ${this.t('panel.common.cancel')}
          </button>
          <button class="row-action rule-save" id="rule-save" type="button" disabled>
            ${this.t('panel.common.save')}
          </button>
        </div>
      </form>
      ${rulesListHtml}
    `;
  },

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
  },

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
      this._announceMode(this.t('panel.regles.mode.yaml'));
    } else {
      // yaml -> form: allowed only when the text validates - never lose
      // content silently. The validated config becomes the mapping.
      if (!this._yamlValidated) {
        this._announceMode(
          this.t('panel.regles.mode.form'),
          this._yamlError && this._yamlError.message
            ? this.t('panel.regles.mode.switch_refused', {
                msg: this.t(this._yamlError.message),
              })
            : this.t('panel.regles.mode.switch_refused_generic')
        );
        return;
      }
      this._mapping = this._yamlValidated;
      this._ruleForm = null;
      this._rulesMode = 'form';
      const content = this.shadowRoot.getElementById('tab-content');
      content.innerHTML = this._renderRulesTab();
      this._wireRulesTab();
      this._announceMode(this.t('panel.regles.mode.form'));
    }
  },

  _announceMode(mode, extra = '') {
    const status = this.shadowRoot.getElementById('rules-status');
    if (status) {
      // The refused extra composes inside {mode} so the announced text
      // matches the pre-i18n rendering: the mode name and the refusal
      // suffix are announced as one sentence.
      status.textContent = this.t('panel.regles.mode.announce', {
        mode: extra ? `${mode} — ${extra}` : mode,
      });
    }
  },

  _scheduleYamlValidation() {
    if (this._yamlTimer) {
      clearTimeout(this._yamlTimer);
    }
    this._yamlTimer = setTimeout(() => this._validateYaml(), 400);
  },

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
          'panel.regles.validation.invalid';
        this._yamlError = { message, line: this._yamlLineFromError(message, text) };
        this._yamlValidated = null;
      }
    } catch (err) {
      // Syntax errors arrive as websocket errors carrying "line N"
      const message = (err && (err.message || err.code)) ||
        'panel.regles.validation.unavailable';
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
  },

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
  },

  _updateYamlState() {
    const errEl = this.shadowRoot.getElementById('yaml-error');
    const saveBtn = this.shadowRoot.getElementById('yaml-save');
    if (errEl) {
      errEl.textContent = this._yamlError
        ? this.t('panel.regles.yaml.error_line', {
            n: this._yamlError.line || '?',
            msg: this.t(this._yamlError.message),
          })
        : '';
    }
    if (saveBtn) {
      saveBtn.disabled = !this._yamlValidated ||
        this._saveState === 'saving' ||
        this._saveState === 'applying';
      saveBtn.textContent =
        this._saveState === 'saving'
          ? this.t('panel.common.saving')
          : this._saveState === 'applying'
            ? this.t('panel.common.applying')
            : this.t('panel.common.save');
    }
  },

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
  },

  _renderYamlHighlight() {
    const editor = this.shadowRoot.getElementById('yaml-editor');
    const pre = this.shadowRoot.getElementById('yaml-highlight');
    const gutter = this.shadowRoot.getElementById('yaml-gutter');
    if (!editor || !pre || !gutter) {
      return;
    }
    const lines = editor.value.split('\n');
    gutter.textContent = lines.map((_, i) => i + 1).join('\n') + '\n';
    pre.innerHTML = lines.map((line) => this._highlightYamlLine(line)).join('\n');
    this._syncYamlScroll();
  },

  _highlightYamlLine(line) {
    // Full-line comment
    if (/^\s*#/.test(line)) {
      return `<span class="tok-comment">${this._escapeHtml(line)}</span>`;
    }
    // Trailing comment (heuristic: whitespace before #)
    let code = line;
    let comment = '';
    const commentIdx = line.search(/\s#/);
    if (commentIdx !== -1) {
      code = line.slice(0, commentIdx + 1);
      comment = `<span class="tok-comment">${this._escapeHtml(line.slice(commentIdx + 1))}</span>`;
    }
    // Key up to the first colon, highlighted value after it
    const colonIdx = code.indexOf(':');
    let html;
    if (colonIdx === -1) {
      html = this._highlightYamlValue(code);
    } else {
      const key = code.slice(0, colonIdx);
      const value = code.slice(colonIdx + 1);
      html = `<span class="tok-key">${this._escapeHtml(key)}</span>:`
        + this._highlightYamlValue(value);
    }
    return html + comment;
  },

  _highlightYamlValue(text) {
    // Quoted strings are parked as placeholders first so the number and
    // boolean rules never recolor their content.
    let out = this._escapeHtml(text);
    const strings = [];
    out = out.replace(/&quot;[\s\S]*?&quot;|&#39;[\s\S]*?&#39;/g, (m) => {
      strings.push(`<span class="tok-str">${m}</span>`);
      return `\u0000${strings.length - 1}\u0000`;
    });
    out = out
      .replace(/\b(true|false|null)\b/g,
        '<span class="tok-bool">$1</span>')
      .replace(/(^|\s)(-?\d+(?:\.\d+)?)(?=\s|$)/gm,
        (m, prefix, num) => `${prefix}<span class="tok-num">${num}</span>`);
    return out.replace(/\u0000(\d+)\u0000/g, (m, i) => strings[i]);
  },

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
  },

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
  },

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
  },

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
  },

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
  },
  });
}
