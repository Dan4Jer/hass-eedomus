"""Light entity for eedomus integration."""

from __future__ import annotations

import logging

from homeassistant.components.light import (
    ATTR_RGB_COLOR,  # MODIFICATION : Ajout du support de l'attribut RGB pour le mode autonome et Hue
)
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_RGBW_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util.color import color_rgbw_to_rgb

from .const import COORDINATOR, DOMAIN
from .entity import EedomusEntity, map_device_to_ha_entity
from .mapping_registry import register_device_mapping

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up eedomus lights from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    entities = []

    # devices = coordinator.data.get("periph_list", {}).get("body", [])
    all_peripherals = coordinator.get_all_peripherals()
    parent_to_children = {}

    for periph_id, periph in all_peripherals.items():
        if periph.get("parent_periph_id"):
            parent_id = periph["parent_periph_id"]
            if parent_id not in parent_to_children:
                parent_to_children[parent_id] = []
            parent_to_children[parent_id].append(periph)
        if "ha_entity" not in coordinator.data[periph_id]:
            eedomus_mapping = map_device_to_ha_entity(
                periph, coordinator.data, coordinator=coordinator
            )
            coordinator.data[periph_id].update(eedomus_mapping)
            # S'assurer que le mapping est enregistré dans le registre global
            register_device_mapping(eedomus_mapping, periph["name"], periph_id, periph)
            # Log pour confirmer que le device a été mappé
            _LOGGER.debug(
                "✅ Light device mapped: %s (%s) → %s:%s",
                periph["name"],
                periph_id,
                eedomus_mapping["ha_entity"],
                eedomus_mapping["ha_subtype"],
            )

    for periph_id, periph in all_peripherals.items():
        ha_entity = None
        if "ha_entity" in coordinator.data[periph_id]:
            ha_entity = coordinator.data[periph_id]["ha_entity"]

        parent_id = periph.get("parent_periph_id", None)
        if parent_id and coordinator.data[parent_id]["ha_entity"] == "light":
            # les enfants sont gérés par le parent... est-ce une bonne idée ?
            eedomus_mapping = None
            if periph.get("usage_id") == "1":
                eedomus_mapping = {
                    "ha_entity": "light",
                    "ha_subtype": "brightness",
                    "justification": "Parent is a light",
                }
            # Removed usage_id=82 mapping as it's now handled by the main mapping system as "select"
            if periph.get("usage_id") == "26":
                eedomus_mapping = {
                    "ha_entity": "sensor",
                    "ha_subtype": "energy",
                    "justification": "Parent is a light - energy consumption meter",
                }
            if eedomus_mapping is not None:
                coordinator.data[periph_id].update(eedomus_mapping)
                _LOGGER.debug(
                    "Created energy sensor for light %s (%s) - consumption monitoring",
                    periph["name"],
                    periph_id,
                )

    for periph_id, periph in all_peripherals.items():
        ha_entity = None
        if "ha_entity" in coordinator.data[periph_id]:
            ha_entity = coordinator.data[periph_id]["ha_entity"]

        if ha_entity is None or not ha_entity == "light":
            continue

        _LOGGER.debug(
            "Go for a light !!! %s (%s) mapping=%s", periph["name"], periph_id, periph
        )
        if "light" in coordinator.data[periph_id].get("ha_entity", None):
            # MODIFICATION : Changement de la détection pour intercepter "rgb" ou "rgbw" et analyser le nombre d'enfants
            periph_subtype = coordinator.data[periph_id].get("ha_subtype", "") or ""
            if "rgb" in periph_subtype or "rgbw" in periph_subtype:
                children = parent_to_children.get(periph_id, [])
                if len(children) >= 4:
                    # Créer une entité RGBW agrégée (Z-Wave avec canaux séparés R, G, B, W)
                    entities.append(
                        EedomusRGBWLight(
                            coordinator,
                            periph_id,
                            parent_to_children[periph_id],
                        )
                    )
                elif len(children) == 1:
                    # MODIFICATION HUE : Un seul enfant qui porte la couleur sous forme de chaîne (ex: Hue "0,25,100")
                    _LOGGER.debug(
                        "Create a single child RGB light entity for Hue/Zipato: %s (%s)",
                        periph["name"],
                        periph_id,
                    )
                    entities.append(
                        EedomusRGBChildLight(coordinator, periph_id, children[0])
                    )
                else:
                    # MODIFICATION STANDALONE : Pas d'enfant (ex: ESP32/WLED) ou fallback si < 4 enfants
                    _LOGGER.debug(
                        "Create a standalone RGB/RGBW light entity (no children or fallback): %s (%s)",
                        periph["name"],
                        periph_id,
                    )
                    entities.append(EedomusLight(coordinator, periph_id))
            else:
                _LOGGER.debug(
                    "Create a light entity %s (%s)", periph["name"], periph_id
                )
                entities.append(EedomusLight(coordinator, periph_id))

    async_add_entities(entities)


class EedomusLight(EedomusEntity, LightEntity):
    """Representation of an eedomus light."""

    def __init__(self, coordinator, periph_id):
        """Initialize the light."""
        super().__init__(coordinator, periph_id)
        self._attr_supported_color_modes = {ColorMode.ONOFF}
        self._attr_rgb_color = None
        self._attr_rgbw_color = None  # MODIFICATION : Ajout du support de l'attribut interne RGBW pour le mode autonome
        self._attr_brightness = None
        self._attr_color_temp_kelvin = None
        self._attr_xy_color = None
        periph_info = self.coordinator.data[periph_id]
        periph_type = periph_info.get("ha_subtype")
        periph_name = periph_info.get("name")

        # MODIFICATION : Séparation nette entre le mode "rgb" et "rgbw" pour les périphériques autonomes
        if periph_type == "brightness" or periph_type == "dimmable":
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        elif periph_type == "rgb":
            self._attr_supported_color_modes = {ColorMode.RGB}
        elif periph_type == "rgbw":
            self._attr_supported_color_modes = {ColorMode.RGBW}
        elif periph_type == "color_temp":
            self._attr_supported_color_modes = {ColorMode.COLOR_TEMP}
        else:
            # Default to ONOFF if no specific type
            self._attr_supported_color_modes = {ColorMode.ONOFF}

        _LOGGER.debug(
            "Using supported_color_modes for %s (%s): %s",
            periph_name,
            periph_id,
            self._attr_supported_color_modes,
        )

        _LOGGER.debug(
            "Initializing light entity for %s (%s) type=%s, supported_color_modes=%s",
            periph_name,
            periph_id,
            periph_type,
            self._attr_supported_color_modes,
        )

    @property
    def is_on(self):
        """Return true if the light is on."""
        # Check if coordinator data is available
        if self.coordinator.data is None:
            _LOGGER.warning(
                f"Coordinator data is None for light {self._periph_id}, assuming off"
            )
            return False

        # Check if device data exists
        device_data = self.coordinator.data.get(self._periph_id)
        if device_data is None:
            _LOGGER.warning(
                f"Device data not found in coordinator for light {self._periph_id}, assuming off"
            )
            return False

        value = device_data.get("last_value")
        if value is None or value == "None":
            return False

        # 🚨 CORRECTION : La lumière est éteinte si la valeur est "0", 0 ou "off"
        return str(value).lower() not in {"0", "off"}

    # MODIFICATION : Propriété dynamique color_mode pour gérer proprement le mode RGB et RGBW autonome
    @property
    def color_mode(self):
        """Return the color mode of the light."""
        if ColorMode.RGBW in self._attr_supported_color_modes:
            return ColorMode.RGBW
        if ColorMode.RGB in self._attr_supported_color_modes:
            return ColorMode.RGB
        if ColorMode.BRIGHTNESS in self._attr_supported_color_modes:
            return ColorMode.BRIGHTNESS
        if ColorMode.COLOR_TEMP in self._attr_supported_color_modes:
            return ColorMode.COLOR_TEMP
        return ColorMode.ONOFF

    # MODIFICATION : Ajout de la propriété de lecture rgb_color pour le mode autonome (ex: "255,0,0")
    @property
    def rgb_color(self):
        """Return the rgb color value for standalone RGB lights."""
        if ColorMode.RGB not in self._attr_supported_color_modes:
            return None
        value = self.coordinator.data.get(self._periph_id, {}).get("last_value", "")
        if isinstance(value, str) and "," in value:
            try:
                parts = [int(x.strip()) for x in value.split(",")]
                if len(parts) >= 3:
                    return (parts[0], parts[1], parts[2])
            except ValueError:
                pass
        return (255, 255, 255)

    # MODIFICATION : Ajout de la propriété de lecture rgbw_color pour le mode autonome (ex: "255,0,0,100")
    @property
    def rgbw_color(self):
        """Return the rgbw color value for standalone RGBW lights."""
        if ColorMode.RGBW not in self._attr_supported_color_modes:
            return None
        value = self.coordinator.data.get(self._periph_id, {}).get("last_value", "")
        if isinstance(value, str) and "," in value:
            try:
                parts = [int(x.strip()) for x in value.split(",")]
                if len(parts) >= 4:
                    return (parts[0], parts[1], parts[2], parts[3])
            except ValueError:
                pass
        return (255, 255, 255, 255)

    @property
    def brightness(self):
        """Return the brightness of the light (0-255)."""
        if not self.is_on:
            return 0

        # Get the current brightness value from eedomus (0-100 percentage)
        periph_data = self._get_periph_data()
        if periph_data is None:
            _LOGGER.warning(
                f"Cannot get brightness: peripheral data not found for {self._periph_id}"
            )
            return 0

        brightness_percent = periph_data.get("last_value", "0")

        # MODIFICATION :
        #    Si c'est une chaîne de couleur (ex: "255,100,50"),
        #        l'état d'intensité est considéré comme maximal
        if isinstance(brightness_percent, str) and "," in brightness_percent:
            return 255

        try:
            # Convert percentage (0-100) to octal (0-255) for Home Assistant
            if brightness_percent == "on":
                return 255  # Full brightness
            brightness_octal = self.percent_to_octal(int(brightness_percent))
            _LOGGER.debug(
                "Brightness for %s (%s): percent=%s, octal=%s",
                self._attr_name,
                self._periph_id,
                brightness_percent,
                brightness_octal,
            )
            return brightness_octal
        except (ValueError, TypeError):
            _LOGGER.warning(
                "Invalid brightness value '%s' for %s (%s)",
                brightness_percent,
                self._attr_name,
                self._periph_id,
            )
            return 255  # Default to full brightness if value is invalid

    @property
    def supported_color_modes(self):
        """Flag supported color modes."""
        return self._attr_supported_color_modes

    async def async_turn_on(self, **kwargs):
        """Turn the light on."""
        _LOGGER.debug(
            "Turning on light %s (%s) with kwargs: %s",
            self._attr_name,
            self._periph_id,
            kwargs,
        )
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        rgb_color = kwargs.get(
            ATTR_RGB_COLOR
        )  # MODIFICATION : Capture du changement de couleur RGB (WLED/ESP32)
        rgbw_color = kwargs.get(ATTR_RGBW_COLOR)
        color_temp_kelvin = kwargs.get(ATTR_COLOR_TEMP_KELVIN)

        # MODIFICATION : Prise en charge des commandes RGB et RGBW autonomes dans la construction de l'API eedomus
        if rgb_color is not None:
            value = f"{rgb_color[0]},{rgb_color[1]},{rgb_color[2]}"
        elif rgbw_color is not None:
            value = (
                f"rgbw:{rgbw_color[0]},{rgbw_color[1]},{rgbw_color[2]},{rgbw_color[3]}"
            )
        elif color_temp_kelvin is not None:
            value = f"color_temp:{color_temp_kelvin}"
        elif brightness is not None:
            brightness_percent = self.octal_to_percent(brightness)
            value = str(brightness_percent)
        else:
            value = "100"  # Default to 100% if no brightness specified

        try:
            # Use entity method to turn on light (includes fallback, retry, and state update)
            response = await self.async_set_value(value)
            _LOGGER.debug(
                "Light %s (%s) turned on with value: %s (brightness: %s%%). API Response: %s",
                self._attr_name,
                self._periph_id,
                value,
                (
                    self.octal_to_percent(brightness)
                    if brightness is not None
                    else "default"
                ),
                response,
            )

        except Exception as e:
            _LOGGER.error(
                "Failed to turn on light %s (%s): %s",
                self._attr_name,
                self._periph_id,
                e,
            )
            raise

    async def async_turn_off(self, **kwargs):
        """Turn the light off."""
        _LOGGER.debug("Turning off light %s", self._periph_id)
        response = None
        try:
            # Use entity method to turn off light (includes fallback, retry, and state update)
            response = await self.async_set_value("0")

        except Exception as e:
            _LOGGER.error(
                "Failed to turn off light %s (%s): %s. API Response: %s",
                self._attr_name,
                self._periph_id,
                e,
                response,
            )
            raise

    def percent_to_octal(self, percent: float) -> int:
        """Convertit un pourcentage (0-100) en valeur 0-255."""
        return round(percent * 255 / 100)

    def octal_to_percent(self, brightness: int) -> int:
        """Convertit une valeur 0-255 en pourcentage (0-100).

        Conversion directe sans arrondi pour une précision maximale.
        """
        return int(brightness * 100 / 255)


# MODIFICATION HUE : Classe dédiée au cas Maître (Intensité) / Enfant unique (Chaîne de couleur en pourcentage)
class EedomusRGBChildLight(EedomusLight):
    """Représentation d'une lumière eedomus avec un seul enfant portant la couleur (ex: Philips Hue)."""

    def __init__(self, coordinator, periph_id, color_child):
        """Initialiser la lumière Hue."""
        super().__init__(coordinator, periph_id)
        self._color_child_id = color_child["periph_id"]

        periph_subtype = self.coordinator.data[periph_id].get("ha_subtype", "rgb")
        if periph_subtype == "rgbw":
            self._attr_supported_color_modes = {ColorMode.RGBW}
            self._color_mode = ColorMode.RGBW
        else:
            self._attr_supported_color_modes = {ColorMode.RGB}
            self._color_mode = ColorMode.RGB

    @property
    def color_mode(self):
        """Retourner le mode de couleur actuel."""
        return self._color_mode

    @property
    def supported_color_modes(self):
        """Retourner les modes de couleur supportés."""
        return self._attr_supported_color_modes

    @property
    def rgb_color(self):
        """Calculer la couleur RGB depuis la chaîne de l'enfant (ex: "0,25,100" en %)."""
        if ColorMode.RGB not in self._attr_supported_color_modes:
            return None
        value = self.coordinator.data.get(self._color_child_id, {}).get(
            "last_value", ""
        )
        if isinstance(value, str) and "," in value:
            try:
                parts = [int(x.strip()) for x in value.split(",")]
                if len(parts) >= 3:
                    # eedomus transmet les valeurs Hue en pourcentage (0-100). Conversion en base 255 pour HA.
                    return (
                        self.percent_to_octal(parts[0]),
                        self.percent_to_octal(parts[1]),
                        self.percent_to_octal(parts[2]),
                    )
            except ValueError:
                pass
        return (255, 255, 255)

    @property
    def rgbw_color(self):
        """Calculer la couleur RGBW depuis la chaîne de l'enfant si applicable."""
        if ColorMode.RGBW not in self._attr_supported_color_modes:
            return None
        value = self.coordinator.data.get(self._color_child_id, {}).get(
            "last_value", ""
        )
        if isinstance(value, str) and "," in value:
            try:
                parts = [int(x.strip()) for x in value.split(",")]
                if len(parts) >= 4:
                    return (
                        self.percent_to_octal(parts[0]),
                        self.percent_to_octal(parts[1]),
                        self.percent_to_octal(parts[2]),
                        self.percent_to_octal(parts[3]),
                    )
                elif len(parts) == 3:
                    return (
                        self.percent_to_octal(parts[0]),
                        self.percent_to_octal(parts[1]),
                        self.percent_to_octal(parts[2]),
                        0,
                    )
            except ValueError:
                pass
        return (255, 255, 255, 255)

    async def async_turn_on(self, **kwargs):
        """Allumer la lumière en modifiant l'enfant pour la couleur et le parent pour la luminosité."""
        _LOGGER.debug(
            "Turning on Hue light %s (%s) with kwargs: %s",
            self._attr_name,
            self._periph_id,
            kwargs,
        )

        # 1. Si la couleur change, actionner le périphérique ENFANT avec les pourcentages eedomus
        if (
            ATTR_RGB_COLOR in kwargs
            and ColorMode.RGB in self._attr_supported_color_modes
        ):
            r, g, b = kwargs[ATTR_RGB_COLOR]
            val_str = f"{self.octal_to_percent(r)},{self.octal_to_percent(g)},{self.octal_to_percent(b)}"
            await self.coordinator.async_set_periph_value(self._color_child_id, val_str)
        elif (
            ATTR_RGBW_COLOR in kwargs
            and ColorMode.RGBW in self._attr_supported_color_modes
        ):
            r, g, b, w = kwargs[ATTR_RGBW_COLOR]
            val_str = (
                f"{self.octal_to_percent(r)},"
                f"{self.octal_to_percent(g)},"
                f"{self.octal_to_percent(b)},"
                f"{self.octal_to_percent(w)}"
            )
            await self.coordinator.async_set_periph_value(self._color_child_id, val_str)

        # 2. Actionner l'intensité / état sur le périphérique PARENT
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            await self.async_set_value(str(self.octal_to_percent(brightness)))
        else:
            current_val = self.coordinator.data[self._periph_id].get("last_value", "0")
            if current_val in ("0", "off"):
                await self.async_set_value("100")
            else:
                await self.async_set_value(str(current_val))

        self.async_write_ha_state()


class EedomusRGBWLight(EedomusLight):
    """Representation of an eedomus RGBW light, aggregating child devices (R, G, B, W)."""

    def __init__(self, coordinator, periph_id, child_devices):
        """Initialize the RGBW light with parent and child devices."""
        super().__init__(coordinator, periph_id)
        self._parent_id = periph_id
        self._parent_device = self.coordinator.data[periph_id]
        self._child_devices = {child["periph_id"]: child for child in child_devices}
        self._color_mode = ColorMode.RGBW
        self._supported_color_modes = {
            # ColorMode.ONOFF,
            ColorMode.RGBW
            #           ColorMode.XY,  # Ajoute le support du mode XY
            #           ColorMode.COLOR_TEMP
        }
        _LOGGER.debug(
            "Using supported_color_modes for RGBW light: %s",
            self._supported_color_modes,
        )
        self._global_brightness_percent = 0
        self._red_percent = 0
        self._green_percent = 0
        self._blue_percent = 0
        self._white_percent = 0
        _ = self.rgbw_color  # to setup x percent values

    @property
    def color_mode(self):
        """Return the color mode of the light."""
        return self._color_mode

    @property
    def supported_color_modes(self):
        """Flag supported color modes."""
        return self._supported_color_modes

    @property
    def is_on(self):
        """Return true if any child channel is on."""
        _LOGGER.debug(
            "Light RGBW %s is_on: %s => should be %s-%s %s with children=%s",
            self.coordinator.data[self._periph_id]["name"],
            self._global_brightness_percent,
            self.coordinator.data[self._periph_id]["ha_subtype"],
            self.coordinator.data[self._periph_id].get("last_value", "Unknown"),
            self.coordinator.data[self._periph_id].get("last_value_change", "Unknown"),
            ", ".join(
                f"{self.coordinator.data[child_id].get('name', child_id)} "
                f"({self.coordinator.data[child_id].get('usage_name', '?')}-{child_id})"
                f"[{self.coordinator.data[child_id].get('last_value', '?')} => "
                f"{self.coordinator.data[child_id].get('last_value_change', '?')}] "
                f"{self.coordinator.data[child_id].get('ha_entity', '!')}"
                for child_id in self._child_devices.keys()
            ),
        )
        return self._global_brightness_percent > 0

    @property
    def brightness(self):
        """Return the brightness of the light (average of all channels)."""
        self._global_brightness_percent = int(
            self.coordinator.data[self._parent_id].get("last_value", 0)
        )

        return self.percent_to_octal(self._global_brightness_percent)

    @property
    def rgbw_color(self):
        """Return the RGBW color value."""
        # Vérifier qu'il y a bien 4 enfants (R, G, B, W)
        if len(self._child_devices) < 4:
            _LOGGER.error(
                "RGBW light '%s' does not have 4 child devices (has %d)",
                self.coordinator.data[self._parent_id]["name"],
                len(self._child_devices),
            )
            return None

        # Trier les enfants par periph_id pour garantir l'ordre numérique
        # Les périphériques eedomus ont toujours leurs enfants dans l'ordre numérique
        child_list = sorted(self._child_devices.keys(), key=lambda x: int(x))
        red_child = child_list[0]
        green_child = child_list[1]
        blue_child = child_list[2]
        white_child = child_list[3]

        _LOGGER.debug(
            "RGBW light '%s' - Sorted children by periph_id: %s",
            self.coordinator.data[self._parent_id]["name"],
            child_list,
        )

        # Extraire les valeurs avec gestion des différents formats
        def safe_extract_value(value):
            """Extraire une valeur numérique à partir de différents formats."""
            if not value or value == "0" or value == "off":
                return 0

            # Gestion du format "r,g,b,w" (ex: "15,40,30,100")
            if isinstance(value, str) and "," in value:
                parts = value.split(",")
                if len(parts) == 4:
                    # C'est probablement un format RGBW complet
                    # Nous devons déterminer quel canal correspond
                    # Pour l'instant, retournons la moyenne
                    try:
                        return sum(int(p.strip()) for p in parts) // 4
                    except (ValueError, AttributeError):
                        return 0
                else:
                    # Format inattendu, essayer de prendre la première valeur
                    try:
                        return int(parts[0].strip())
                    except (ValueError, IndexError, AttributeError):
                        return 0

            # Gestion des valeurs normales (pourcentage 0-100)
            try:
                if isinstance(value, str) and value.endswith("%"):
                    return int(value[:-1])
                return int(value)
            except (ValueError, TypeError):
                return 0

        self._red_percent = safe_extract_value(
            self.coordinator.data[red_child].get("last_value", 0)
        )
        self._green_percent = safe_extract_value(
            self.coordinator.data[green_child].get("last_value", 0)
        )
        self._blue_percent = safe_extract_value(
            self.coordinator.data[blue_child].get("last_value", 0)
        )
        self._white_percent = safe_extract_value(
            self.coordinator.data[white_child].get("last_value", 0)
        )
        self._global_brightness_percent = int(
            self.coordinator.data[self._parent_id].get("last_value", 0)
        )
        _LOGGER.debug(
            "RGBW color '%s' with (%d,%d,%d,%d){%d} - R:%s, G:%s, B:%s, W:%s",
            self.coordinator.data[self._parent_id]["name"],
            self._red_percent,
            self._green_percent,
            self._blue_percent,
            self._white_percent,
            self._global_brightness_percent,
            red_child,
            green_child,
            blue_child,
            white_child,
        )
        return (
            self.percent_to_octal(self._red_percent),
            self.percent_to_octal(self._green_percent),
            self.percent_to_octal(self._blue_percent),
            self.percent_to_octal(self._white_percent),
        )

    @property
    def xy_color(self):
        """Retourne les coordonnées xy de la couleur actuelle."""
        return self._attr_xy_color

    async def async_turn_on(self, **kwargs):
        """Turn the light on with optional color and brightness."""
        _LOGGER.debug(
            "Turning on RGBW light '%s' with params: %s => %s%%",
            self.coordinator.data[self._parent_id]["name"],
            kwargs,
            (
                self.octal_to_percent(kwargs[ATTR_BRIGHTNESS])
                if ATTR_BRIGHTNESS in kwargs
                else "?"
            ),
        )

        if kwargs == {}:
            _LOGGER.debug(
                "Turning on '%s'... try to use the last kwown value data =%s",
                self.coordinator.data[self._parent_id]["name"],
                self.coordinator.data[self._parent_id],
            )
            self._global_brightness_percent = int(
                self.coordinator.data[self._parent_id].get("last_value", 100)
            )
            if not self._global_brightness_percent > 0:
                self._global_brightness_percent = 100

        # Vérifier qu'il y a bien 4 enfants (R, G, B, W)
        if len(self._child_devices) < 4:
            _LOGGER.error(
                "RGBW light '%s' does not have 4 child devices (has %d)",
                self.coordinator.data[self._parent_id]["name"],
                len(self._child_devices),
            )
            return

        # Trier les enfants par periph_id pour garantir l'ordre numérique
        # Les périphériques eedomus ont toujours leurs enfants dans l'ordre numérique
        child_list = sorted(self._child_devices.keys(), key=lambda x: int(x))
        red_periph_id = child_list[0]
        green_periph_id = child_list[1]
        blue_periph_id = child_list[2]
        white_periph_id = child_list[3]

        _LOGGER.debug(
            "RGBW light '%s' - Sorted children by periph_id: %s",
            self.coordinator.data[self._parent_id]["name"],
            child_list,
        )

        if ATTR_BRIGHTNESS in kwargs:
            self._global_brightness_percent = self.octal_to_percent(
                kwargs[ATTR_BRIGHTNESS]
            )
        if ATTR_RGBW_COLOR in kwargs:
            r, g, b, w = kwargs[ATTR_RGBW_COLOR]
            self._red_percent = self.octal_to_percent(r)
            await self.coordinator.async_set_periph_value(
                red_periph_id, self._red_percent
            )
            self._green_percent = self.octal_to_percent(g)
            await self.coordinator.async_set_periph_value(
                green_periph_id, self._green_percent
            )
            self._blue_percent = self.octal_to_percent(b)
            await self.coordinator.async_set_periph_value(
                blue_periph_id, self._blue_percent
            )
            self._white_percent = self.octal_to_percent(w)
            await self.coordinator.async_set_periph_value(
                white_periph_id, self._white_percent
            )
            self._global_brightness_percent = self.octal_to_percent(max(r, g, b, w))
            self._attr_rgbw_color = (r, g, b, w)
            self._attr_rgb_color = color_rgbw_to_rgb(r, g, b, w)
        #           self._attr_xy_color = color_util.color_RGB_to_xy(self._attr_rgb_color)
        #           self._attr_color_temp_kelvin = color_util.color_rgb_to_kelvin(self._attr_rgb_color)
        await self.coordinator.async_set_periph_value(
            self._parent_id, self._global_brightness_percent
        )

        self._attr_is_on = self._global_brightness_percent > 0
        self._attr_brightness = int(self._global_brightness_percent)
        self.async_write_ha_state()
        self.schedule_update_ha_state()
        await self.coordinator.async_request_refresh()  # a essayer

    async def async_turn_off(self, **kwargs):
        """Turn the light off."""
        self._global_brightness_percent = 0
        await self.coordinator.async_set_periph_value(
            self._parent_id, self._global_brightness_percent
        )
        # Éteindre tous les canaux enfants pour une extinction complète
        if self._child_devices:
            for child_id in self._child_devices:
                await self.coordinator.async_set_periph_value(child_id, "0")
        self.schedule_update_ha_state()
        await self.coordinator.async_request_refresh()
