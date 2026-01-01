# Implémentation des Capteurs de Batterie comme Entités Enfants

## 🎯 Approche Recommandée

Cette documentation explique comment implémenter les capteurs de batterie comme des entités enfants directement dans le code principal de l'intégration, sans fichier séparé.

## 📋 Concept

Les capteurs de batterie doivent être créés comme des **entités enfants** des périphériques principaux lorsque ceux-ci ont des informations de batterie. Cela permet :

1. **Une meilleure organisation** - Les batteries font partie des périphériques
2. **Un rafraîchissement synchronisé** - Mis à jour avec les données du parent
3. **Moins de code** - Pas besoin d'une classe séparée
4. **Une intégration native** - Utilise directement `SensorEntity` avec `device_class="battery"`

## 🔧 Implémentation

### 1. Dans le fichier principal (probablement dans le coordinator ou l'entité de base)

```python
from homeassistant.components.sensor import SensorEntity

class EedomusDeviceEntity(EedomusEntity):
    """Base class for eedomus device entities."""
    
    def __init__(self, coordinator, periph_id):
        super().__init__(coordinator, periph_id)
        # ... autre initialisation ...
        
        # Create battery child entity if device has battery
        self._battery_entity = self._create_battery_entity()
    
    def _create_battery_entity(self):
        """Create battery child entity if device has valid battery data."""
        battery_level = self.coordinator.data[self._periph_id].get("battery")
        
        if battery_level and battery_level.strip():
            try:
                battery_value = int(battery_level)
                if 0 <= battery_value <= 100:
                    return EedomusBatteryChildEntity(self.coordinator, self._periph_id, self)
            except ValueError:
                _LOGGER.warning("Invalid battery level for %s: %s", 
                              self.name, battery_level)
        
        return None
    
    @property
    def battery_entity(self):
        """Return the battery child entity if exists."""
        return self._battery_entity


class EedomusBatteryChildEntity(SensorEntity):
    """
    Simple battery child entity using native SensorEntity.
    
    This class directly extends SensorEntity with device_class='battery'
    instead of creating a separate platform.
    """
    
    def __init__(self, coordinator, periph_id, parent_entity):
        """Initialize the battery child entity."""
        self._coordinator = coordinator
        self._periph_id = periph_id
        self._parent_entity = parent_entity
        
        # Configure entity attributes
        self._attr_name = f"{parent_entity.name} Battery"
        self._attr_unique_id = f"{periph_id}_battery"
        self._attr_device_class = "battery"
        self._attr_native_unit_of_measurement = "%"
        self._attr_state_class = "measurement"
        
        _LOGGER.debug("Created battery child entity for %s", parent_entity.name)
    
    @property
    def native_value(self) -> int | None:
        """Return the battery level."""
        battery_level = self._coordinator.data[self._periph_id].get("battery", "")
        
        if battery_level and battery_level.strip():
            try:
                return int(battery_level)
            except ValueError:
                _LOGGER.warning("Invalid battery level for %s: %s", 
                              self._attr_name, battery_level)
        
        return None
    
    @property
    def available(self) -> bool:
        """Return True if battery data is available."""
        battery_level = self._coordinator.data[self._periph_id].get("battery", "")
        return battery_level and battery_level.strip() and battery_level.isdigit()
    
    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        return {
            "parent_device": self._parent_entity.name,
            "parent_device_id": self._parent_entity.unique_id,
            "battery_status": self._get_battery_status()
        }
    
    def _get_battery_status(self) -> str:
        """Get battery status based on level."""
        level = self.native_value
        
        if level is None:
            return "Unknown"
        if level >= 75:
            return "High"
        if level >= 50:
            return "Medium"
        if level >= 25:
            return "Low"
        return "Critical"
    
    async def async_update(self) -> None:
        """Update the battery entity."""
        # The coordinator update will refresh the data
        await self._coordinator.async_request_refresh()
        
        battery_level = self._coordinator.data[self._periph_id].get("battery", "")
        _LOGGER.debug("Updated battery for %s: %s%%", self._attr_name, battery_level)


class EedomusDeviceFactory:
    """Factory class to create device entities with battery children."""
    
    def create_device_entities(self, periph_id, periph_data):
        """Create all entities for a device, including battery if applicable."""
        entities = []
        
        # 1. Create main entity based on device type
        main_entity = self._create_main_entity(periph_id, periph_data)
        entities.append(main_entity)
        
        # 2. Create battery child entity if device has battery
        battery_level = periph_data.get("battery")
        if battery_level and battery_level.strip():
            try:
                battery_value = int(battery_level)
                if 0 <= battery_value <= 100:
                    battery_entity = EedomusBatteryChildEntity(
                        self._coordinator, 
                        periph_id, 
                        main_entity
                    )
                    entities.append(battery_entity)
                    _LOGGER.info("Created battery sensor for %s (%s%%)", 
                               main_entity.name, battery_value)
            except ValueError:
                _LOGGER.warning("Invalid battery level for %s: %s", 
                              main_entity.name, battery_level)
        
        return entities


# Alternative: Create battery entities directly in the coordinator
class EedomusDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator that creates battery entities inline."""
    
    def __init__(self, hass, client):
        super().__init__(hass, _LOGGER, name="eedomus")
        self._client = client
        self._battery_entities = {}
    
    async def _async_update_data(self):
        """Fetch data and create/update battery entities."""
        data = await self._client.async_get_data()
        
        # Update existing battery entities
        self._update_battery_entities(data)
        
        return data
    
    def _update_battery_entities(self, data):
        """Create or update battery entities based on device data."""
        for periph_id, periph_data in data.items():
            battery_level = periph_data.get("battery")
            
            # Check if we need to create a new battery entity
            if battery_level and battery_level.strip():
                if periph_id not in self._battery_entities:
                    self._create_battery_entity(periph_id, periph_data)
                else:
                    self._update_battery_entity(periph_id, periph_data)
    
    def _create_battery_entity(self, periph_id, periph_data):
        """Create a new battery entity."""
        try:
            battery_value = int(periph_data.get("battery", 0))
            if 0 <= battery_value <= 100:
                # Find the main entity for this device
                main_entity = self._find_main_entity(periph_id)
                
                if main_entity:
                    battery_entity = EedomusBatteryChildEntity(
                        self, periph_id, main_entity
                    )
                    self._battery_entities[periph_id] = battery_entity
                    
                    # Add to Home Assistant
                    async_add_entities([battery_entity], True)
                    
                    _LOGGER.info("Created battery sensor for %s", main_entity.name)
        except ValueError:
            _LOGGER.warning("Invalid battery level for device %s", periph_id)
    
    def _update_battery_entity(self, periph_id, periph_data):
        """Update existing battery entity."""
        if periph_id in self._battery_entities:
            entity = self._battery_entities[periph_id]
            entity.async_write_ha_state()


# Example of how to register entities in the main setup
async def async_setup_entry(hass, entry):
    """Main setup entry that creates all entities."""
    coordinator = EedomusDataUpdateCoordinator(hass, client)
    
    # Get all devices
    all_devices = await coordinator.async_config_entry_first_refresh()
    
    # Create entities for each device
    entities = []
    for periph_id, periph_data in all_devices.items():
        device_entities = create_device_entities(periph_id, periph_data)
        entities.extend(device_entities)
    
    # Add all entities to Home Assistant
    async_add_entities(entities, True)


# Utility function to create device entities
def create_device_entities(periph_id, periph_data):
    """Create main entity and battery child if applicable."""
    entities = []
    
    # 1. Create main entity based on usage_id
    main_entity = create_main_entity(periph_id, periph_data)
    entities.append(main_entity)
    
    # 2. Create battery child entity if device has battery
    battery_level = periph_data.get("battery")
    if battery_level and battery_level.strip():
        try:
            battery_value = int(battery_level)
            if 0 <= battery_value <= 100:
                battery_entity = EedomusBatteryChildEntity(
                    coordinator, periph_id, main_entity
                )
                entities.append(battery_entity)
        except ValueError:
            pass  # Invalid battery level, skip
    
    return entities


## 🎯 Avantages de cette Approche

✅ **Plus simple** - Pas de fichier séparé nécessaire
✅ **Plus intégré** - Les batteries font partie des périphériques
✅ **Plus maintenable** - Moins de code à gérer
✅ **Plus flexible** - Peut être adapté à différents types de périphériques
✅ **Plus performant** - Pas de plateforme séparée à charger

## 📋 Exemple de Données

### Périphérique avec Batterie
```json
{
  "periph_id": "1090995",
  "name": "Mouvement Oeil de chat Salon",
  "usage_id": "37",
  "battery": "85",
  "value": "0"
}
```

### Entités Créées
1. **Entité principale** : `binary_sensor.mouvement_oeil_de_chat_salon`
2. **Entité enfant batterie** : `sensor.mouvement_oeil_de_chat_salon_battery`

### Affichage dans Home Assistant
```
Mouvement Oeil de chat Salon
├── État: 0 (pas de mouvement)
└── Batterie: 85% (entité enfant)
   ├── Statut: High
   ├── Parent: Mouvement Oeil de chat Salon
   └── Device Class: battery
```

## 🔧 Intégration avec le Système Existant

### Dans le fichier principal (ex: __init__.py)
```python
# Import the battery child entity class
from .battery_child import EedomusBatteryChildEntity

# In your entity creation logic
def create_device_entities(self, periph_id, periph_data):
    """Create entities for a device."""
    entities = []
    
    # Create main entity
    main_entity = self._create_main_entity(periph_id, periph_data)
    entities.append(main_entity)
    
    # Create battery child if applicable
    if periph_data.get("battery"):
        battery_entity = EedomusBatteryChildEntity(
            self.coordinator, periph_id, main_entity
        )
        entities.append(battery_entity)
    
    return entities
```

### Dans le fichier manifest.json
```json
{
  "domain": "eedomus",
  "name": "Eedomus",
  "documentation": "https://github.com/Dan4Jer/hass-eedomus",
  "issue_tracker": "https://github.com/Dan4Jer/hass-eedomus/issues",
  "dependencies": [],
  "codeowners": ["@Dan4Jer"],
  "requirements": [],
  "iot_class": "local_polling",
  "config_flow": true
}
```

## 📊 Types de Périphériques Supportés

| Type de Périphérique | usage_id | Exemple | Batterie Supportée |
|----------------------|----------|---------|-------------------|
| Détecteur de Mouvement | 37 | "Mouvement Salon" | ✅ Oui |
| Capteur de Température | 7 | "Température Salon" | ✅ Oui |
| Détecteur de Fumée | 1 | "Fumée Cuisine" | ✅ Oui |
| Détecteur d'Inondation | 2 | "Inondation Salle de bain" | ✅ Oui |
| Détecteur de Porte | 3 | "Porte Entrée" | ✅ Oui |
| Interrupteur | 2 | "Lampe Salon" | ❌ Non (sauf si batterie) |

## 💡 Bonnes Pratiques

1. **Toujours vérifier** que la valeur de batterie est valide avant de créer l'entité
2. **Utiliser device_class="battery"** pour une intégration native
3. **Fournir des attributs utiles** comme le statut et le périphérique parent
4. **Gérer les erreurs** gracieusement pour les valeurs invalides
5. **Logger les informations** pour le débogage

## 🎉 Conclusion

Cette approche permet de créer des capteurs de batterie de manière simple et intégrée, directement comme des entités enfants des périphériques principaux. Elle est plus propre et plus maintenable que d'avoir une plateforme séparée.

Pour implémenter cette solution, il suffit d'ajouter la logique de création des entités enfants dans le code principal de l'intégration, là où les périphériques sont traités.

Si vous avez besoin d'aide pour intégrer cette solution dans votre code existant, n'hésitez pas à demander !