# Integration du Rich Editor dans Home Assistant 2026+

## Problème Identifié

Dans Home Assistant 2026+, le paramètre `custom_ui` n'est plus supporté dans `async_show_form()`. L'API a changé et nécessite une approche différente pour intégrer les composants frontend personnalisés.

## Solution pour HA 2026+

### 1. Chargement Automatique des Ressources Frontend

Home Assistant 2026+ charge automatiquement les ressources frontend depuis le répertoire `www/` des intégrations. Notre composant `eedomus-rich-editor.js` est déjà correctement placé et sera chargé.

### 2. Approches Alternatives pour l'Intégration

#### Option A: Utiliser un Panel Personnalisé (Recommandé)

Créer un panel personnalisé qui utilise notre rich editor :

```python
# Dans __init__.py ou un fichier de panel dédié
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # ... setup code ...
    
    # Register custom panel
    if not hass.components.frontend.async_register_built_in_panel(
        hass,
        "eedomus-config",
        "eedomus-config",
        "mdi:cog",
        require_admin=True,
    ):
        _LOGGER.warning("Could not register Eedomus config panel")
    
    return True
```

#### Option B: Utiliser un Lovelace Card

Créer une carte Lovelace qui utilise notre composant :

```javascript
// Dans un fichier eedomus-card.js
class EedomusConfigCard extends HTMLElement {
  setConfig(config) {
    // Create our rich editor
    const editor = document.createElement('eedomus-rich-editor');
    editor.setConfig(config);
    this.appendChild(editor);
  }
}

customElements.define('eedomus-config-card', EedomusConfigCard);
```

#### Option C: Remplacer l'Options Flow (Avancé)

Pour une intégration complète, nous pouvons créer un custom flow handler :

```python
# Créer un fichier custom_flow.py
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_entry_oauth2_flow

class EedomusRichConfigFlow(config_entry_oauth2_flow.AbstractOAuth2FlowHandler):
    # Implémentation personnalisée
    pass
```

### 3. Solution Actuelle Implémentée

Actuellement, nous utilisons l'éditeur YAML standard comme fallback, mais le rich editor est disponible et peut être utilisé via :

```javascript
// Dans n'importe quel composant frontend
const editor = document.createElement('eedomus-rich-editor');
editor.setConfig({
    name: "My Config",
    custom_devices: []
});
document.body.appendChild(editor);
```

### 4. Migration vers une Solution Complète

Pour une intégration complète, nous recommandons :

1. **Créer un panel personnalisé** pour une expérience utilisateur optimale
2. **Utiliser les WebSocket endpoints** déjà implémentés pour la communication
3. **Charger dynamiquement** le composant quand nécessaire

### 5. Code de Test pour le Frontend

Voici comment tester que notre composant est bien chargé :

```javascript
// Dans la console du navigateur
if (customElements.get('eedomus-rich-editor')) {
    console.log('✅ Rich editor is registered');
    
    const editor = document.createElement('eedomus-rich-editor');
    editor.setConfig({
        name: "Test",
        custom_devices: [
            {
                device_id: "test",
                device_type: "light",
                name: "Test Light"
            }
        ]
    });
    document.body.appendChild(editor);
} else {
    console.log('❌ Rich editor not found');
}
```

### 6. Vérification des Fichiers Frontend

Les fichiers suivants sont déployés et devraient être accessibles :

- `/local/custom_components/eedomus/www/eedomus-rich-editor.js`
- `/local/custom_components/eedomus/www/manifest.json`
- `/local/custom_components/eedomus/www/eedomus-frontend-config.json`

### 7. Prochaines Étapes

Pour une intégration complète dans HA 2026+ :

1. **Créer un panel personnalisé** dans le menu latéral
2. **Utiliser les WebSocket endpoints** pour la communication backend
3. **Implémenter la sauvegarde** via les services existants
4. **Ajouter la validation en temps réel**

## Références

- [HA Frontend Documentation](https://developers.home-assistant.io/docs/frontend/)
- [Custom Panels](https://developers.home-assistant.io/docs/frontend/custom-panels/)
- [Web Components](https://developer.mozilla.org/en-US/docs/Web/Web_Components)