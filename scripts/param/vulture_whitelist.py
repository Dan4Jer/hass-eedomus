# vulture_whitelist.py
# Fichier lu uniquement par Vulture pour ignorer les faux positifs liés à Home Assistant
post
_handle_coordinator_update
_async_update_data

# --- Fonctions de cycle de vie (__init__.py) ---
async_setup
async_setup_entry
async_unload_entry
async_remove_entry
async_remove_config_entry

# --- Fonctions de Configuration (config_flow.py / options_flow.py) ---
EedomusConfigFlow
async_step_user
async_step_yaml
async_step_init
async_get_options_flow
async_step_uninstall
async_step_ui
VERSION
# --- Plateformes (sensor.py, light.py, etc.) ---
async_setup_platform
async_setup_entry
async_turn_on
async_turn_off
async_stop_cover
async_set_hvac_mode
# --- cover ---
async_open_cover
async_close_cover
is_closed
current_cover_position
current_cover_tilt_position
async_set_cover_tilt_position
# --- climate ---
available
temperature_unit
# --- light ---
color_mode
supported_color_modes
xy_color
# --- Attributs standards de classe HA ---
_attr_has_entity_name
_attr_should_poll
_attr_translation_key
# 
# --- gardé dans eedomus_client.py ---
# --- appel standard a l'API Eedomus pour le moment non utilisé ---
get_periph_value
get_periph_history
get_periph_info
get_device_history_count
#
# gardé dans mapping_registry.py 
# 
clear_mapping_registry
get_mapping_registry 
print_mapping_summary
# 
# --- select.py
current_option
async_select_option
# 
# --- sensor.py
state_class
native_unit_of_measurement

