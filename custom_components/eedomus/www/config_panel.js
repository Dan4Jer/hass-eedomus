/**
 * Eedomus Configuration Panel - Lovelace Card for HA 2026.1+
 * 
 * Modern Lovelace card implementation using HA's card helpers
 */

class EedomusConfigPanelCard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this._hass = null;
        this._config = {};
        this._loading = true;
        this._currentConfig = 'default';
        this._entityProperties = {};
        this._deviceOverrides = {};
        this._devices = [];
    }

    setConfig(config) {
        if (!config) {
            throw new Error('Configuration not provided');
        }
        
        this._config = config;
        this._loadData();
    }

    set hass(hass) {
        this._hass = hass;
        if (this._hass) {
            this._loadData();
        }
    }

    connectedCallback() {
        if (!this._config) {
            this._renderLoading();
            return;
        }
        
        this._render();
        this._setupEventListeners();
    }

    disconnectedCallback() {
        // Clean up event listeners
    }

    _render() {
        if (this._loading) {
            this._renderLoading();
            return;
        }
        
        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    --card-background: var(--ha-card-background, white);
                    --primary-color: var(--primary-color, #1a73e8);
                    --text-color: var(--primary-text-color, #323335);
                    --secondary-text: var(--secondary-text-color, #616161);
                    --divider-color: var(--divider-color, #e0e0e0);
                    --disabled-color: var(--disabled-text-color, #9e9e9e);
                    --accent-color: var(--accent-color, #03a9f4);
                }

                .card {
                    background: var(--card-background);
                    border-radius: var(--ha-card-border-radius, 12px);
                    padding: 24px;
                    color: var(--text-color);
                    font-family: var(--ha-font-family, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif);
                }

                .header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 24px;
                }

                .title {
                    font-size: 20px;
                    font-weight: 500;
                    color: var(--primary-color);
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }

                .config-switcher {
                    display: flex;
                    gap: 8px;
                    align-items: center;
                }

                .config-button {
                    padding: 8px 16px;
                    border: 1px solid var(--divider-color);
                    background: var(--card-background);
                    color: var(--text-color);
                    border-radius: 8px;
                    cursor: pointer;
                    transition: all 0.2s;
                    font-size: 14px;
                }

                .config-button.active {
                    background: var(--primary-color);
                    color: white;
                    border-color: var(--primary-color);
                }

                .config-button:hover {
                    background: var(--primary-color);
                    color: white;
                }

                .tabs {
                    display: flex;
                    gap: 16px;
                    border-bottom: 1px solid var(--divider-color);
                    margin-bottom: 24px;
                    overflow-x: auto;
                }

                .tab {
                    padding: 12px 0;
                    cursor: pointer;
                    border-bottom: 2px solid transparent;
                    color: var(--secondary-text);
                    white-space: nowrap;
                    font-size: 14px;
                }

                .tab.active {
                    border-bottom-color: var(--primary-color);
                    color: var(--primary-color);
                    font-weight: 500;
                }

                .tab-content {
                    display: none;
                }

                .tab-content.active {
                    display: block;
                    animation: fadeIn 0.3s;
                }

                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }

                .section {
                    margin-bottom: 24px;
                }

                .section-title {
                    font-size: 16px;
                    font-weight: 500;
                    margin-bottom: 16px;
                    color: var(--primary-color);
                }

                .entity-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                    gap: 16px;
                }

                .entity-card {
                    background: var(--card-background);
                    border-radius: 8px;
                    padding: 16px;
                    border: 1px solid var(--divider-color);
                    transition: all 0.2s;
                }

                .entity-card:hover {
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }

                .entity-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 12px;
                }

                .entity-name {
                    font-weight: 500;
                    font-size: 15px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }

                .toggle-switch {
                    position: relative;
                    display: inline-block;
                    width: 44px;
                    height: 22px;
                }

                .toggle-switch input {
                    opacity: 0;
                    width: 0;
                    height: 0;
                }

                .slider {
                    position: absolute;
                    cursor: pointer;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background-color: var(--disabled-color);
                    transition: .4s;
                    border-radius: 22px;
                }

                .slider:before {
                    position: absolute;
                    content: "";
                    height: 16px;
                    width: 16px;
                    left: 3px;
                    bottom: 3px;
                    background-color: white;
                    transition: .4s;
                    border-radius: 50%;
                }

                input:checked + .slider {
                    background-color: var(--primary-color);
                }

                input:checked + .slider:before {
                    transform: translateX(22px);
                }

                .device-list {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
                    gap: 16px;
                }

                .device-card {
                    background: var(--card-background);
                    border-radius: 8px;
                    padding: 16px;
                    border: 1px solid var(--divider-color);
                    transition: all 0.2s;
                }

                .device-card:hover {
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }

                .device-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 12px;
                }

                .device-name {
                    font-weight: 500;
                    font-size: 15px;
                }

                .device-id {
                    font-size: 12px;
                    color: var(--secondary-text);
                    margin-bottom: 10px;
                    word-break: break-all;
                }

                .device-info {
                    display: flex;
                    gap: 12px;
                    margin-bottom: 12px;
                    font-size: 13px;
                    flex-wrap: wrap;
                }

                .info-item {
                    display: flex;
                    align-items: center;
                    gap: 4px;
                }

                .badge {
                    display: inline-flex;
                    align-items: center;
                    gap: 4px;
                    padding: 4px 10px;
                    border-radius: 12px;
                    font-size: 11px;
                    font-weight: 500;
                }

                .badge.override {
                    background: var(--primary-color);
                    color: white;
                }

                .badge.entity {
                    background: var(--accent-color);
                    color: white;
                }

                .badge.fallback {
                    background: var(--divider-color);
                    color: var(--secondary-text);
                }

                .actions {
                    display: flex;
                    gap: 8px;
                    justify-content: flex-end;
                    margin-top: 12px;
                }

                .btn {
                    padding: 6px 12px;
                    border: none;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 12px;
                    font-weight: 500;
                    transition: all 0.2s;
                    height: 28px;
                }

                .btn-primary {
                    background: var(--primary-color);
                    color: white;
                }

                .btn-primary:hover {
                    opacity: 0.9;
                }

                .btn-secondary {
                    background: var(--card-background);
                    color: var(--text-color);
                    border: 1px solid var(--divider-color);
                }

                .btn-secondary:hover {
                    background: var(--divider-color);
                }

                .stats {
                    display: flex;
                    gap: 16px;
                    margin-bottom: 20px;
                    overflow-x: auto;
                    padding-bottom: 8px;
                }

                .stat-card {
                    background: var(--card-background);
                    padding: 12px 16px;
                    border-radius: 8px;
                    border: 1px solid var(--divider-color);
                    text-align: center;
                    min-width: 100px;
                }

                .stat-value {
                    font-size: 18px;
                    font-weight: 500;
                    color: var(--primary-color);
                }

                .stat-label {
                    font-size: 12px;
                    color: var(--secondary-text);
                    margin-top: 4px;
                }

                .search-bar {
                    margin-bottom: 20px;
                    position: relative;
                }

                .search-input {
                    width: 100%;
                    padding: 10px 36px 10px 12px;
                    border: 1px solid var(--divider-color);
                    border-radius: 8px;
                    background: var(--card-background);
                    color: var(--text-color);
                    font-size: 14px;
                }

                .search-icon {
                    position: absolute;
                    right: 12px;
                    top: 50%;
                    transform: translateY(-50%);
                    color: var(--secondary-text);
                }

                .empty-state {
                    text-align: center;
                    padding: 32px;
                    color: var(--secondary-text);
                }

                .empty-icon {
                    font-size: 36px;
                    margin-bottom: 12px;
                }

                .loading {
                    text-align: center;
                    padding: 40px;
                }

                .spinner {
                    border: 3px solid var(--disabled-color);
                    border-top: 3px solid var(--primary-color);
                    border-radius: 50%;
                    width: 36px;
                    height: 36px;
                    animation: spin 1s linear infinite;
                    margin: 0 auto 16px;
                }

                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }

                .description {
                    color: var(--secondary-text);
                    font-size: 13px;
                    margin-bottom: 16px;
                }
            </style>

            <div class="card">
                <div class="header">
                    <div class="title">
                        <ha-icon icon="mdi:cog-transfer"></ha-icon>
                        <span>Eedomus Configuration</span>
                    </div>
                    <div class="config-switcher">
                        <span style="font-size: 13px; color: var(--secondary-text);">Config:</span>
                        <button class="config-button ${this._currentConfig === 'default' ? 'active' : ''}" data-config="default">Default</button>
                        <button class="config-button ${this._currentConfig === 'custom' ? 'active' : ''}" data-config="custom">Custom</button>
                        <button class="btn btn-secondary" id="reload-btn">↻ Reload</button>
                    </div>
                </div>

                <div class="tabs">
                    <div class="tab active" data-tab="entity-properties">Entity Properties</div>
                    <div class="tab" data-tab="device-overrides">Device Overrides</div>
                    <div class="tab" data-tab="device-list">All Devices</div>
                </div>

                <div class="tab-content active" id="entity-properties-tab">
                    <div class="section">
                        <div class="section-title">Dynamic Entity Properties</div>
                        <div class="description">
                            Configure which entity types should receive frequent updates
                        </div>
                        <div class="entity-grid" id="entity-grid"></div>
                    </div>
                </div>

                <div class="tab-content" id="device-overrides-tab">
                    <div class="section">
                        <div class="section-title">Specific Device Overrides</div>
                        <div class="description">
                            Override dynamic behavior for individual devices by periph_id
                        </div>
                        <div class="search-bar">
                            <input type="text" class="search-input" id="device-search" placeholder="Search devices...">
                            <span class="search-icon">🔍</span>
                        </div>
                        <div class="stats" id="override-stats"></div>
                        <div class="device-list" id="device-overrides-list"></div>
                    </div>
                </div>

                <div class="tab-content" id="device-list-tab">
                    <div class="section">
                        <div class="section-title">All Devices Status</div>
                        <div class="description">
                            View dynamic status and configuration for all devices
                        </div>
                        <div class="stats" id="device-stats"></div>
                        <div class="search-bar">
                            <input type="text" class="search-input" id="all-devices-search" placeholder="Search all devices...">
                            <span class="search-icon">🔍</span>
                        </div>
                        <div class="device-list" id="all-devices-list"></div>
                    </div>
                </div>
            </div>
        `;
    }

    _renderLoading() {
        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                }
                .card {
                    background: var(--ha-card-background, white);
                    border-radius: var(--ha-card-border-radius, 12px);
                    padding: 24px;
                    text-align: center;
                }
                .spinner {
                    border: 3px solid #e0e0e0;
                    border-top: 3px solid #1a73e8;
                    border-radius: 50%;
                    width: 40px;
                    height: 40px;
                    animation: spin 1s linear infinite;
                    margin: 0 auto 16px;
                }
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            </style>
            <div class="card">
                <div class="spinner"></div>
                <div>Loading Eedomus Configuration...</div>
            </div>
        `;
    }

    async _loadData() {
        if (!this._hass || !this._config) {
            return;
        }

        this._loading = true;
        this._render();

        try {
            // Get the card instance from hass
            const card = this._hass.data["eedomus"]?.config_panel_card;
            
            if (card) {
                const data = await card.async_get_config();
                this._currentConfig = data.current_config;
                this._entityProperties = data.dynamic_entity_properties;
                this._deviceOverrides = data.specific_device_overrides;
                this._devices = data.devices;
            } else {
                // Fallback data
                this._entityProperties = {
                    light: true, switch: true, binary_sensor: true,
                    sensor: false, climate: false, cover: true,
                    select: false, scene: false
                };
                this._deviceOverrides = {};
                this._devices = [];
            }
            
            this._loading = false;
            this._render();
            this._renderEntityProperties();
            this._renderDeviceOverrides();
            this._renderAllDevices();
            this._setupEventListeners();
            
        } catch (error) {
            console.error('Failed to load config data:', error);
            this._loading = false;
            this._render();
        }
    }

    _setupEventListeners() {
        // Tab switching
        this.shadowRoot.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                this.shadowRoot.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                this.shadowRoot.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                
                tab.classList.add('active');
                const tabId = tab.getAttribute('data-tab');
                this.shadowRoot.getElementById(tabId + '-tab').classList.add('active');
            });
        });

        // Config switching
        this.shadowRoot.querySelectorAll('.config-button').forEach(button => {
            button.addEventListener('click', () => {
                const configName = button.getAttribute('data-config');
                this._switchConfig(configName);
            });
        });

        // Reload button
        const reloadBtn = this.shadowRoot.getElementById('reload-btn');
        if (reloadBtn) {
            reloadBtn.addEventListener('click', () => {
                this._reloadConfig();
            });
        }

        // Search functionality
        const deviceSearch = this.shadowRoot.getElementById('device-search');
        if (deviceSearch) {
            deviceSearch.addEventListener('input', (e) => {
                this._filterDeviceOverrides(e.target.value);
            });
        }

        const allDevicesSearch = this.shadowRoot.getElementById('all-devices-search');
        if (allDevicesSearch) {
            allDevicesSearch.addEventListener('input', (e) => {
                this._filterAllDevices(e.target.value);
            });
        }
    }

    async _switchConfig(configName) {
        try {
            const card = this._hass.data["eedomus"]?.config_panel_card;
            if (card && await card.async_switch_config(configName)) {
                this._currentConfig = configName;
                await this._loadData();
            }
        } catch (error) {
            console.error('Failed to switch config:', error);
        }
    }

    async _reloadConfig() {
        try {
            const card = this._hass.data["eedomus"]?.config_panel_card;
            if (card && await card.async_reload_config()) {
                await this._loadData();
            }
        } catch (error) {
            console.error('Failed to reload config:', error);
        }
    }

    _renderEntityProperties() {
        const grid = this.shadowRoot.getElementById('entity-grid');
        if (!grid) return;
        
        grid.innerHTML = '';

        const entities = [
            { type: 'light', icon: 'mdi:lightbulb', label: 'Lights' },
            { type: 'switch', icon: 'mdi:toggle-switch', label: 'Switches' },
            { type: 'binary_sensor', icon: 'mdi:eye', label: 'Binary Sensors' },
            { type: 'sensor', icon: 'mdi:chart-line', label: 'Sensors' },
            { type: 'climate', icon: 'mdi:thermostat', label: 'Climate' },
            { type: 'cover', icon: 'mdi:window-shutter', label: 'Covers' },
            { type: 'select', icon: 'mdi:form-dropdown', label: 'Selects' },
            { type: 'scene', icon: 'mdi:palette', label: 'Scenes' }
        ];

        entities.forEach(entity => {
            const isDynamic = this._entityProperties[entity.type] || false;
            
            const card = document.createElement('div');
            card.className = 'entity-card';
            card.innerHTML = `
                <div class="entity-header">
                    <div class="entity-name">
                        <ha-icon icon="${entity.icon}" style="color: var(--primary-color);"></ha-icon>
                        <span>${entity.label}</span>
                    </div>
                    <label class="toggle-switch">
                        <input type="checkbox" ${isDynamic ? 'checked' : ''} data-entity-type="${entity.type}">
                        <span class="slider"></span>
                    </label>
                </div>
                <div style="font-size: 12px; color: var(--secondary-text);">
                    ${isDynamic ? 'Dynamic updates enabled' : 'Static (no frequent updates)'}
                </div>
            `;
            
            grid.appendChild(card);
        });

        // Add event listeners
        grid.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', async (e) => {
                const entityType = e.target.getAttribute('data-entity-type');
                const isDynamic = e.target.checked;
                await this._updateEntityProperty(entityType, isDynamic);
            });
        });
    }

    _renderDeviceOverrides() {
        const list = this.shadowRoot.getElementById('device-overrides-list');
        const stats = this.shadowRoot.getElementById('override-stats');
        
        if (!list || !stats) return;
        
        list.innerHTML = '';
        
        // Calculate stats
        const dynamicCount = Object.values(this._deviceOverrides).filter(v => v).length;
        const staticCount = Object.values(this._deviceOverrides).filter(v => !v).length;
        
        stats.innerHTML = `
            <div class="stat-card">
                <div class="stat-value">${Object.keys(this._deviceOverrides).length}</div>
                <div class="stat-label">Overrides</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${dynamicCount}</div>
                <div class="stat-label">Dynamic</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${staticCount}</div>
                <div class="stat-label">Static</div>
            </div>
        `;

        if (Object.keys(this._deviceOverrides).length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📋</div>
                    <div>No specific device overrides</div>
                    <div style="font-size: 12px; margin-top: 8px; color: var(--disabled-color);">
                        Add overrides to customize individual devices
                    </div>
                </div>
            `;
            return;
        }

        // Render devices with overrides
        this._devices.forEach(device => {
            if (device.periph_id in this._deviceOverrides) {
                const isDynamic = this._deviceOverrides[device.periph_id];
                
                const card = document.createElement('div');
                card.className = 'device-card';
                card.innerHTML = `
                    <div class="device-header">
                        <div class="device-name">${device.name}</div>
                        <div class="actions">
                            <button class="btn btn-secondary remove-override" data-periph-id="${device.periph_id}">Remove</button>
                        </div>
                    </div>
                    <div class="device-id">${device.periph_id}</div>
                    <div class="device-info">
                        <div class="info-item">
                            <ha-icon icon="mdi:tag" style="font-size: 14px;"></ha-icon>
                            <span>${device.ha_entity}</span>
                        </div>
                        <div class="info-item">
                            <ha-icon icon="mdi:numeric" style="font-size: 14px;"></ha-icon>
                            <span>${device.usage_id}</span>
                        </div>
                    </div>
                    <div style="margin-bottom: 12px;">
                        <span class="badge override">
                            <ha-icon icon="mdi:cog" style="font-size: 12px;"></ha-icon>
                            <span>Manual Override</span>
                        </span>
                    </div>
                    <div class="entity-header">
                        <span style="font-size: 13px; color: var(--secondary-text);">Dynamic updates</span>
                        <label class="toggle-switch">
                            <input type="checkbox" ${isDynamic ? 'checked' : ''} data-periph-id="${device.periph_id}">
                            <span class="slider"></span>
                        </label>
                    </div>
                `;
                
                list.appendChild(card);
            }
        });

        // Add event listeners
        list.querySelectorAll('.remove-override').forEach(button => {
            button.addEventListener('click', async (e) => {
                const periphId = e.target.getAttribute('data-periph-id');
                await this._removeDeviceOverride(periphId);
            });
        });

        list.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', async (e) => {
                const periphId = e.target.getAttribute('data-periph-id');
                const isDynamic = e.target.checked;
                await this._updateDeviceOverride(periphId, isDynamic);
            });
        });
    }

    _renderAllDevices() {
        const list = this.shadowRoot.getElementById('all-devices-list');
        const stats = this.shadowRoot.getElementById('device-stats');
        
        if (!list || !stats) return;
        
        list.innerHTML = '';
        
        // Calculate stats
        const dynamicCount = this._devices.filter(d => d.is_dynamic).length;
        const staticCount = this._devices.filter(d => !d.is_dynamic).length;
        const overrideCount = Object.keys(this._deviceOverrides).length;
        
        stats.innerHTML = `
            <div class="stat-card">
                <div class="stat-value">${this._devices.length}</div>
                <div class="stat-label">Total</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${dynamicCount}</div>
                <div class="stat-label">Dynamic</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${staticCount}</div>
                <div class="stat-label">Static</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${overrideCount}</div>
                <div class="stat-label">Overrides</div>
            </div>
        `;

        if (this._devices.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🔌</div>
                    <div>No devices found</div>
                    <div style="font-size: 12px; margin-top: 8px; color: var(--disabled-color);">
                        Devices will appear after loading from eedomus
                    </div>
                </div>
            `;
            return;
        }

        // Render all devices
        this._devices.forEach(device => {
            const isOverride = device.periph_id in this._deviceOverrides;
            const badgeClass = isOverride ? 'override' : (device.is_dynamic ? 'entity' : 'fallback');
            const badgeIcon = isOverride ? 'mdi:cog' : (device.is_dynamic ? 'mdi:chart-line' : 'mdi:help');
            const badgeText = isOverride ? 'Manual Override' : (device.is_dynamic ? 'Entity Type' : 'Fallback');
            
            const card = document.createElement('div');
            card.className = 'device-card';
            card.innerHTML = `
                <div class="device-header">
                    <div class="device-name">${device.name}</div>
                    ${isOverride ? `
                        <div class="actions">
                            <button class="btn btn-secondary remove-override" data-periph-id="${device.periph_id}">Remove</button>
                        </div>
                    ` : ''}
                </div>
                <div class="device-id">${device.periph_id}</div>
                <div class="device-info">
                    <div class="info-item">
                        <ha-icon icon="mdi:tag" style="font-size: 14px;"></ha-icon>
                        <span>${device.ha_entity}</span>
                    </div>
                    <div class="info-item">
                        <ha-icon icon="mdi:numeric" style="font-size: 14px;"></ha-icon>
                        <span>${device.usage_id}</span>
                    </div>
                </div>
                <div style="margin-bottom: 12px;">
                    <span class="badge ${badgeClass}">
                        <ha-icon icon="${badgeIcon}" style="font-size: 12px;"></ha-icon>
                        <span>${badgeText}</span>
                    </span>
                </div>
                <div class="entity-header">
                    <span style="font-size: 13px; color: var(--secondary-text);">Dynamic updates</span>
                    <label class="toggle-switch">
                        <input type="checkbox" ${device.is_dynamic ? 'checked' : ''} 
                               data-periph-id="${device.periph_id}" 
                               ${isOverride ? '' : 'disabled'}>
                        <span class="slider"></span>
                    </label>
                </div>
            `;
            
            list.appendChild(card);
        });

        // Add event listeners for override removal
        list.querySelectorAll('.remove-override').forEach(button => {
            button.addEventListener('click', async (e) => {
                const periphId = e.target.getAttribute('data-periph-id');
                await this._removeDeviceOverride(periphId);
            });
        });

        // Add event listeners for toggle switches (only for overrides)
        list.querySelectorAll('input[type="checkbox"]:not([disabled])').forEach(checkbox => {
            checkbox.addEventListener('change', async (e) => {
                const periphId = e.target.getAttribute('data-periph-id');
                const isDynamic = e.target.checked;
                await this._updateDeviceOverride(periphId, isDynamic);
            });
        });
    }

    _filterDeviceOverrides(searchTerm) {
        const term = searchTerm.toLowerCase();
        const filteredDevices = this._devices.filter(device => 
            device.periph_id in this._deviceOverrides &&
            (device.name.toLowerCase().includes(term) || 
             device.periph_id.includes(term))
        );
        
        this._renderFilteredDeviceOverrides(filteredDevices);
    }

    _filterAllDevices(searchTerm) {
        const term = searchTerm.toLowerCase();
        const filteredDevices = this._devices.filter(device => 
            device.name.toLowerCase().includes(term) || 
            device.periph_id.includes(term) ||
            device.ha_entity.toLowerCase().includes(term)
        );
        
        this._renderFilteredAllDevices(filteredDevices);
    }

    _renderFilteredDeviceOverrides(devices) {
        const list = this.shadowRoot.getElementById('device-overrides-list');
        if (!list) return;
        
        list.innerHTML = '';

        if (devices.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🔍</div>
                    <div>No matching devices found</div>
                </div>
            `;
            return;
        }

        devices.forEach(device => {
            const isDynamic = this._deviceOverrides[device.periph_id];
            
            const card = document.createElement('div');
            card.className = 'device-card';
            card.innerHTML = `
                <div class="device-header">
                    <div class="device-name">${device.name}</div>
                    <div class="actions">
                        <button class="btn btn-secondary remove-override" data-periph-id="${device.periph_id}">Remove</button>
                    </div>
                </div>
                <div class="device-id">${device.periph_id}</div>
                <div class="device-info">
                    <div class="info-item">
                        <ha-icon icon="mdi:tag" style="font-size: 14px;"></ha-icon>
                        <span>${device.ha_entity}</span>
                    </div>
                    <div class="info-item">
                        <ha-icon icon="mdi:numeric" style="font-size: 14px;"></ha-icon>
                        <span>${device.usage_id}</span>
                    </div>
                </div>
                <div style="margin-bottom: 12px;">
                    <span class="badge override">
                        <ha-icon icon="mdi:cog" style="font-size: 12px;"></ha-icon>
                        <span>Manual Override</span>
                    </span>
                </div>
                <div class="entity-header">
                    <span style="font-size: 13px; color: var(--secondary-text);">Dynamic updates</span>
                    <label class="toggle-switch">
                        <input type="checkbox" ${isDynamic ? 'checked' : ''} data-periph-id="${device.periph_id}">
                        <span class="slider"></span>
                    </label>
                </div>
            `;
            
            list.appendChild(card);
        });

        // Add event listeners
        list.querySelectorAll('.remove-override').forEach(button => {
            button.addEventListener('click', async (e) => {
                const periphId = e.target.getAttribute('data-periph-id');
                await this._removeDeviceOverride(periphId);
            });
        });

        list.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', async (e) => {
                const periphId = e.target.getAttribute('data-periph-id');
                const isDynamic = e.target.checked;
                await this._updateDeviceOverride(periphId, isDynamic);
            });
        });
    }

    _renderFilteredAllDevices(devices) {
        const list = this.shadowRoot.getElementById('all-devices-list');
        if (!list) return;
        
        list.innerHTML = '';

        if (devices.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🔍</div>
                    <div>No matching devices found</div>
                </div>
            `;
            return;
        }

        devices.forEach(device => {
            const isOverride = device.periph_id in this._deviceOverrides;
            const badgeClass = isOverride ? 'override' : (device.is_dynamic ? 'entity' : 'fallback');
            const badgeIcon = isOverride ? 'mdi:cog' : (device.is_dynamic ? 'mdi:chart-line' : 'mdi:help');
            const badgeText = isOverride ? 'Manual Override' : (device.is_dynamic ? 'Entity Type' : 'Fallback');
            
            const card = document.createElement('div');
            card.className = 'device-card';
            card.innerHTML = `
                <div class="device-header">
                    <div class="device-name">${device.name}</div>
                    ${isOverride ? `
                        <div class="actions">
                            <button class="btn btn-secondary remove-override" data-periph-id="${device.periph_id}">Remove</button>
                        </div>
                    ` : ''}
                </div>
                <div class="device-id">${device.periph_id}</div>
                <div class="device-info">
                    <div class="info-item">
                        <ha-icon icon="mdi:tag" style="font-size: 14px;"></ha-icon>
                        <span>${device.ha_entity}</span>
                    </div>
                    <div class="info-item">
                        <ha-icon icon="mdi:numeric" style="font-size: 14px;"></ha-icon>
                        <span>${device.usage_id}</span>
                    </div>
                </div>
                <div style="margin-bottom: 12px;">
                    <span class="badge ${badgeClass}">
                        <ha-icon icon="${badgeIcon}" style="font-size: 12px;"></ha-icon>
                        <span>${badgeText}</span>
                    </span>
                </div>
                <div class="entity-header">
                    <span style="font-size: 13px; color: var(--secondary-text);">Dynamic updates</span>
                    <label class="toggle-switch">
                        <input type="checkbox" ${device.is_dynamic ? 'checked' : ''} 
                               data-periph-id="${device.periph_id}" 
                               ${isOverride ? '' : 'disabled'}>
                        <span class="slider"></span>
                    </label>
                </div>
            `;
            
            list.appendChild(card);
        });

        // Add event listeners for override removal
        list.querySelectorAll('.remove-override').forEach(button => {
            button.addEventListener('click', async (e) => {
                const periphId = e.target.getAttribute('data-periph-id');
                await this._removeDeviceOverride(periphId);
            });
        });

        // Add event listeners for toggle switches (only for overrides)
        list.querySelectorAll('input[type="checkbox"]:not([disabled])').forEach(checkbox => {
            checkbox.addEventListener('change', async (e) => {
                const periphId = e.target.getAttribute('data-periph-id');
                const isDynamic = e.target.checked;
                await this._updateDeviceOverride(periphId, isDynamic);
            });
        });
    }

    async _updateEntityProperty(entityType, isDynamic) {
        try {
            const card = this._hass.data["eedomus"]?.config_panel_card;
            if (card) {
                const success = await card.async_update_config(entityType, isDynamic);
                if (success) {
                    await this._loadData();
                }
            }
        } catch (error) {
            console.error('Failed to update entity property:', error);
            // Show error to user
            this._hass.callService('persistent_notification', 'create', {
                title: 'Eedomus Configuration Error',
                message: `Failed to update ${entityType} property: ${error.message}`,
                notification_id: 'eedomus_config_error'
            });
        }
    }

    async _updateDeviceOverride(periphId, isDynamic) {
        try {
            const card = this._hass.data["eedomus"]?.config_panel_card;
            if (card) {
                const success = await card.async_update_device_override(periphId, isDynamic);
                if (success) {
                    await this._loadData();
                }
            }
        } catch (error) {
            console.error('Failed to update device override:', error);
            this._hass.callService('persistent_notification', 'create', {
                title: 'Eedomus Configuration Error',
                message: `Failed to update device ${periphId}: ${error.message}`,
                notification_id: 'eedomus_config_error'
            });
        }
    }

    async _removeDeviceOverride(periphId) {
        try {
            const card = this._hass.data["eedomus"]?.config_panel_card;
            if (card) {
                const success = await card.async_remove_device_override(periphId);
                if (success) {
                    await this._loadData();
                }
            }
        } catch (error) {
            console.error('Failed to remove device override:', error);
            this._hass.callService('persistent_notification', 'create', {
                title: 'Eedomus Configuration Error',
                message: `Failed to remove device ${periphId}: ${error.message}`,
                notification_id: 'eedomus_config_error'
            });
        }
    }
}

// Register the card
customElements.define('eedomus-config-panel-card', EedomusConfigPanelCard);

// Register the card for Lovelace
if (window.customCards) {
    window.customCards.push({
        type: 'eedomus-config-panel-card',
        name: 'Eedomus Configuration Panel',
        description: 'Configure eedomus device mapping and dynamic properties',
        preview: true,
    });
}