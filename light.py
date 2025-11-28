"""Light entity for eedomus integration."""
from __future__ import annotations

import logging

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_MODE,
    ATTR_RGBW_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)

from homeassistant.util.color import (
    value_to_brightness,
    color_rgb_to_rgbw,
#    color_rgbw_to_rgbw,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .entity import EedomusEntity
from .const import DOMAIN, CLASS_MAPPING

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry_old(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up eedomus light entities from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Get all peripherals
    all_peripherals = coordinator.get_all_peripherals()

    # Filter for lights
    lights = []
    for periph_id, periph in all_peripherals.items():
        usage_name = periph.get("usage_name", "").lower()
        name = periph.get("name", "").lower()

        if ("lampe" in usage_name or
            "light" in usage_name or
            "lampe" in name or
            "light" in name):
            lights.append(EedomusLight(coordinator, periph_id))

    async_add_entities(lights, True)

# ==> Modification proposée: Update entity creation to handle RGBW aggregation
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up eedomus lights from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = []
   
    _LOGGER.debug("Coordinator type: %s", type(coordinator))
    #devices = coordinator.data.get("periph_list", {}).get("body", [])
    all_peripherals = coordinator.get_all_peripherals()
    parent_to_children = {}
    for periph_id, periph in all_peripherals.items():
        if periph.get("parent_periph_id"):
            parent_id = periph["parent_periph_id"]
            if parent_id not in parent_to_children:
                parent_to_children[parent_id] = []
            parent_to_children[parent_id].append(periph)

    #for device in devices:
    #    _LOGGER.debug("setup light: device=%s", device)
    #    if device.get("parent_periph_id"):
    #        parent_id = device["parent_periph_id"]
    #        if parent_id not in parent_to_children:
    #            parent_to_children[parent_id] = []
    #        parent_to_children[parent_id].append(device)

    
    # Create entities
    #for device in devices:
    for periph_id, periph in coordinator.get_all_peripherals().items():
        entity_type = None
        supported_classes = periph.get("SUPPORTED_CLASSES", "").split(",")
        for class_id in supported_classes:
            if class_id in CLASS_MAPPING:
                entity_type = CLASS_MAPPING[class_id]["ha_entity"]
        if not entity_type == "light":
            continue
        coordinator.data[periph_id]["entity_type"] = entity_type
        
        if periph.get("parent_periph_id"):
            continue  # Ignorer les enfants, ils seront gérés par le parent
        
        
        if periph["periph_id"] in parent_to_children:
            # Cas d'un périphérique parent avec des enfants (ex: RGBW)
            children = parent_to_children[periph["periph_id"]]
            _LOGGER.debug("Try to create a RGBW light entity data=%s children=%s", periph, children)
            if any(child.get("usage_name") == "Couleur lumière" for child in children):
                _LOGGER.debug("Create a RGBW light entity data=%s", periph)
                # Créer une entité RGBW agrégée
                entities.append(
                    EedomusRGBWLight(
                        coordinator,
                        periph_id,
                        children,
                    )
                )
            else:
                # Créer une entité light standard
                entities.append(EedomusLight(coordinator, periph_id))
        else:
            # Périphérique sans enfants
            entities.append(EedomusLight(coordinator, periph_id))

    async_add_entities(entities)

    
class EedomusLight(EedomusEntity, LightEntity):
    """Representation of an eedomus light."""

    def __init__(self, coordinator, periph_id):
        """Initialize the light."""
        super().__init__(coordinator, periph_id,)
        self._attr_supported_color_modes = {ColorMode.ONOFF}

        periph_info = self.coordinator.data[periph_id]
        periph_type = periph_info.get("value_type")
        periph_name = periph_info.get("name")

        if periph_type == "rgb":
            self._attr_supported_color_modes.add(ColorMode.RGB)
        elif periph_type == "color_temp":
            self._attr_supported_color_modes.add(ColorMode.COLOR_TEMP)

        _LOGGER.debug(
            "Initializing light entity for %s (%s) type=%s, supported_color_modes=%s",
            periph_name, periph_id, periph_type, self._attr_supported_color_modes
        )

    @property
    def is_on(self):
        """Return true if the light is on."""
        value = self.coordinator.data[self._periph_id].get("last_value")
        #_LOGGER.debug("Light %s (%s) is_on: %s",  self.coordinator.data[self._periph_id]["name"], self._periph_id, value)
        if type(value) == "NoneType" or value == "None":
            return false

        return value == "on"

    async def async_turn_on(self, **kwargs):
        """Turn the light on."""
        _LOGGER.debug("Turning on light %s with kwargs: %s", self._periph_id, kwargs)
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        rgb_color = kwargs.get(ATTR_RGB_COLOR)
        color_temp_kelvin = kwargs.get(ATTR_COLOR_TEMP_KELVIN)

        value = "on"
        if brightness is not None:
            value = f"on:{brightness}"
        if rgb_color is not None:
            value = f"rgb:{rgb_color[0]},{rgb_color[1]},{rgb_color[2]}"
        if color_temp_kelvin is not None:
            value = f"color_temp:{color_temp_kelvin}"

        try:
            response = await self.coordinator.client.set_periph_value(self._periph_id, "100")

            # Correction: le bloc if doit être correctement indenté
            if isinstance(response, dict) and response.get("success") != 1:
                _LOGGER.error("Failed to set light value: %s", response.get("error", "Unknown error"))
                raise Exception(f"Failed to set light value: {response.get('error', 'Unknown error')}")

            await self.coordinator.async_request_refresh()
            _LOGGER.debug("Light %s turned on with value: %s", self._periph_id, value)

        except Exception as e:
            _LOGGER.error("Failed to turn on light %s: %s", self._periph_id, e)
            raise

    async def async_turn_off(self, **kwargs):
        """Turn the light off."""
        _LOGGER.debug("Turning off light %s", self._periph_id)
        try:
            response = await self.coordinator.client.set_periph_value(self._periph_id, 0)
            if isinstance(response, dict) and response.get("success") != 1:
                _LOGGER.error("Failed to turn off light %s: %s", self._periph_id, response.get("error", "Unknown error"))
                raise Exception(f"Failed to turn off light: {response.get('error', 'Unknown error')}")

            await self.coordinator.async_request_refresh()

        except Exception as e:
            _LOGGER.error("Failed to turn off light %s: %s", self._periph_id, e)
            raise


    def percent_to_octal(self, percent: float) -> int:
        """Convertit un pourcentage (0-100) en valeur 0-255."""
        return round(percent * 255 / 100)

    def octal_to_percent(self, brightness: int) -> int:
        """Convertit une valeur 0-255 en pourcentage (0-100)."""
        return round(brightness * 100 / 255)
        
class EedomusRGBWLight(EedomusLight):
    """Representation of an eedomus RGBW light, aggregating child devices (R, G, B, W)."""

    def __init__(self, coordinator, periph_id, child_devices):
        """Initialize the RGBW light with parent and child devices."""
        super().__init__(coordinator, device_info)
        self._parent_device = self.coordinator.data[periph_id]
        self._child_devices = {child["periph_id"]: child for child in child_devices}
        self._color_mode = ColorMode.RGBW
        self._supported_color_modes = {ColorMode.RGBW}
        self._supported_features = LightEntityFeature.EFFECT | LightEntityFeature(0)  # Support pour le mode RGBW
        self._global_brightness_percent = 0
        self._red_percent = 0
        self._green_percent = 0
        self._blue_percent = 0
        self._white_percent = 0
        _ = self.rgbw_color #to setup x percent values
        _LOGGER.debug(
            "Initialized RGBW light '%s' (%s) with children: %s",
            parent_device, self.coordinator.data[parent_device]["name"],
            ", ".join(
                f"{self.coordinator.data[child_id].get('name', child_id)} "
                f"({self.coordinator.data[child_id].get('usage_name', '?')}-{child_id})"
                for child_id in self._child_devices.keys()
            ),
        )

    @property
    def color_mode(self):
        """Return the color mode of the light."""
        return self._color_mode

    @property
    def supported_color_modes(self):
        """Flag supported color modes."""
        return self._supported_color_modes

    @property
    def supported_features(self):
        """Flag supported features."""
        return self._supported_features

    @property
    def is_on(self):
        """Return true if any child channel is on."""
        _LOGGER.debug("Light RGBW %s is_on: %s => should be %s with children=%s",
                      self.coordinator.data[self._periph_id]["name"],
                      self._global_brightness_percent,
                      self.coordinator.data[self._periph_id].get("last_value", "Unknown"),
                      ", ".join(
                          f"{self.coordinator.data[child_id].get('name', child_id)} "
                          f"({self.coordinator.data[child_id].get('usage_name', '?')}-{child_id})[{self.coordinator.data[child_id].get('last_value', '?')}]"
                          for child_id in self._child_devices.keys()
                      ),
                    )
        #self._global_brightness_percent = int(self.coordinator.data[self._periph_id].get("current_value", 0))
        return self._global_brightness_percent > 0

    @property
    def brightness(self):
        """Return the brightness of the light (average of all channels)."""
        self._global_brightness_percent = int(self.coordinator.data[self._parent_device].get("last_value",0))
        _LOGGER.debug("Brightness parent '%s' (%s) %s", self._parent_device,
                      self.coordinator.data[self._parent_device].get("name","Unknown"),
                      self.coordinator.data[self._parent_device].get("last_value",0),
                      )

        return self.percent_to_octal(self._global_brightness_percent)
        
    @property
    def rgbw_color(self):
        """Return the RGBW color value."""
        # Convertir les enfants en liste pour accéder par index
        children = list(self._child_devices.values())

        # Vérifier qu'il y a bien 4 enfants (R, G, B, W)
        if len(children) < 4:
            _LOGGER.error("RGBW light '%s' does not have 4 child devices", self.coordinator.data[self._parent_device]["name"])
            return

        # Récupérer les periph_id des canaux dans l'ordre
        red_periph_id = str(int(self._parent_device) + 1)
        green_periph_id = str(int(self._parent_device) + 2)
        blue_periph_id = str(int(self._parent_device) + 3)
        white_periph_id = str(int(self._parent_device) + 4)

        # Logique pour récupérer les valeurs R, G, B, W depuis les enfants
        _LOGGER.debug("RGBW color child control with children=%s", ", ".join(
                f"{self.coordinator.data[child_id].get('name', child_id)} "
                f"({self.coordinator.data[child_id].get('usage_name', '?')}-{child_id})[{self.coordinator.data[child_id].get('last_value', '?')}]"
                for child_id in self._child_devices.keys()
            ),)
        #self._red_percent = int(self._child_devices[1].get("last_value", 0))
        #self._green_percent = int(self._child_devices[0].get("last_value", 0))
        #self._blue_percent = int(self._child_devices[2].get("last_value", 0))
        #self._white_percent = int(self._child_devices[3].get("last_value", 0))
        self._red_percent = int(self.coordinator.data[red_periph_id].get('last_value', 0))
        self._green_percent = int(self.coordinator.data[green_periph_id].get('last_value', 0))
        self._blue_percent = int(self.coordinator.data[blue_periph_id].get('last_value', 0))
        self._white_percent = int(self.coordinator.data[white_periph_id].get('last_value', 0))
        self._global_brightness_percent = int(self.coordinator.data[self._parent_device].get("last_value",0))
        _LOGGER.debug(
            "RGBW color '%s' with (%d,%d,%d,%d){%d} with children %s",
            self.coordinator.data[self._parent_device]["name"],
            self._red_percent, self._green_percent, self._blue_percent, self._white_percent, self._global_brightness_percent,
            ", ".join(
                f"{self.coordinator.data[child_id].get('name', child_id)} "
                f"({self.coordinator.data[child_id].get('usage_name', '?')}-{child_id})[{self.coordinator.data[child_id].get('last_value', '?')}]"
                for child_id in self._child_devices.keys()
            ),
        )
        return (
            self.percent_to_octal(self._red_percent),
            self.percent_to_octal(self._green_percent),
            self.percent_to_octal(self._blue_percent),
            self.percent_to_octal(self._white_percent),
        )


    async def async_turn_on(self, **kwargs):
        """Turn the light on with optional color and brightness."""
        _LOGGER.debug(
            "Turning on RGBW light '%s' with params: %s => %s%%",
            self.coordinator.data[self._parent_device]["name"],
            kwargs,
            self.octal_to_percent(
                kwargs[ATTR_BRIGHTNESS]
            ) if ATTR_BRIGHTNESS in kwargs else "?",
        )

        if kwargs == {}:
            _LOGGER.debug("Turning on '%s'... try to use the last kwown value data =%s",
                          self.coordinator.data[self._parent_device]["name"],
                          self.coordinator.data[self._parent_device],
                          )
            self._global_brightness_percent = int(self.coordinator.data[self._parent_device].get("last_value", 100))
            if not self._global_brightness_percent > 0:
                self._global_brightness_percent = 100

        # Convertir les enfants en liste pour accéder par index
        children = list(self._child_devices.values())

        # Vérifier qu'il y a bien 4 enfants (R, G, B, W)
        if len(children) < 4:
            _LOGGER.error("RGBW light '%s' does not have 4 child devices", self.coordinator.data[self._parent_device]["name"])
            return

        # Récupérer les periph_id des canaux dans l'ordre
#        red_periph_id = children[1]["periph_id"]
#        green_periph_id = children[0]["periph_id"]
#        blue_periph_id = children[2]["periph_id"]
#        white_periph_id = children[3]["periph_id"]
        red_periph_id = str(int(self._parent_device) + 1)
        green_periph_id = str(int(self._parent_device) + 2)
        blue_periph_id = str(int(self._parent_device) + 3)
        white_periph_id = str(int(self._parent_device) + 4)

        
        if ATTR_BRIGHTNESS in kwargs:
            self._global_brightness_percent = self.octal_to_percent(
                kwargs[ATTR_BRIGHTNESS]
            )
        if ATTR_RGBW_COLOR in kwargs:
            r, g, b, w = kwargs[ATTR_RGBW_COLOR]
            self._red_percent = self.octal_to_percent(r)
            await self.coordinator.async_set_periph_value(red_periph_id, self._red_percent)
            self._green_percent = self.octal_to_percent(g)
            await self.coordinator.async_set_periph_value(green_periph_id, self._green_percent)
            self._blue_percent = self.octal_to_percent(b)
            await self.coordinator.async_set_periph_value(blue_periph_id, self._blue_percent)
            self._white_percent = self.octal_to_percent(w)
            await self.coordinator.async_set_periph_value(white_periph_id, self._white_percent)
            self._global_brightness_percent = self.octal_to_percent(max(r,g,b,w))
        await self.coordinator.async_set_periph_value(self._parent_device, self._global_brightness_percent)

        _LOGGER.debug(
            "Turn on RGBW color '%s' with (%d,%d,%d,%d){%d} with children: %s",
            self.coordinator.data[self._parent_device]["name"],
            self._red_percent, self._green_percent, self._blue_percent, self._white_percent, self._global_brightness_percent,
            ", ".join(
                f"{self.coordinator.data[child_id].get('name', child_id)} "
                f"({self.coordinator.data[child_id].get('usage_name', '?')}-{child_id})[{self.coordinator.data[child_id].get('last_value', '?')}]"
                for child_id in self._child_devices.keys()
            ),
        )

    async def async_turn_off(self, **kwargs):
        """Turn the light off."""
        _LOGGER.debug("Turning off RGBW light '%s'",
                      self.coordinator.data[self._parent_device]["name"])
        self._global_brightness_percent = 0
        await self.coordinator.async_set_periph_value(self._parent_device, self._global_brightness_percent)
        # Éteindre tous les canaux enfants
        #for child_id in self._child_devices:
        #    await self.coordinator.async_set_periph_value(child_id, "off")
