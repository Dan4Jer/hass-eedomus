# Exemple pour enregistrer un service qui envoie une commande directe
async def async_setup_services(hass, coordinator):
async def handle_call(call):
device_id = call.data.get('device_id')
value = call.data.get('value')
await coordinator.client.async_set('set', device_id, value)
await coordinator.async_request_refresh()


hass.services.async_register('eedomus', 'set_value', handle_call)
