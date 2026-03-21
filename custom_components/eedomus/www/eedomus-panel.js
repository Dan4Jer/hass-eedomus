/**
 * Eedomus Configuration Panel for Home Assistant 2026+
 * This panel provides access to the rich configuration editor
 */

class EedomusConfigPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.hass = null;
    this.config = {};
  }

  setConfig(config) {
    if (!config) return;
    this.config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this.config) {
      this._render();
    }
  }

  get hass() {
    return this._hass;
  }

  connectedCallback() {
    if (this.hass) {
      this._render();
    }
  }

  _render() {
    if (!this.shadowRoot) return;

    this.shadowRoot.innerHTML = `
      <style>
        .panel-container {
          padding: 16px;
          max-width: 1200px;
          margin: 0 auto;
        }
        
        .panel-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }
        
        .panel-title {
          font-size: 1.5em;
          font-weight: 500;
          color: var(--primary-text-color);
        }
        
        .panel-content {
          background: white;
          border-radius: 8px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          padding: 16px;
        }
      </style>
      
      <div class="panel-container">
        <div class="panel-header">
          <div class="panel-title">Eedomus Configuration</div>
        </div>
        
        <div class="panel-content">
          <eedomus-rich-editor id="editor"></eedomus-rich-editor>
        </div>
      </div>
    `;

    // Initialize the rich editor when available
    this._initializeEditor();
  }

  _initializeEditor() {
    const editor = this.shadowRoot.getElementById('editor');
    if (editor) {
      // Set initial configuration
      editor.setConfig({
        name: "Eedomus Configuration",
        custom_devices: this.config.custom_devices || []
      });
      
      // Set hass context if available
      if (this.hass) {
        editor.hass = this.hass;
      }
    } else {
      // Retry if editor not yet available
      setTimeout(() => this._initializeEditor(), 100);
    }
  }

  disconnectedCallback() {
    // Cleanup if needed
  }
}

// Register the panel component
if (!customElements.get('eedomus-config-panel')) {
  customElements.define('eedomus-config-panel', EedomusConfigPanel);
  console.log('Eedomus Config Panel registered');
}