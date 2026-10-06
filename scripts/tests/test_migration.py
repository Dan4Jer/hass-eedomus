from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eedomus import async_migrate_entry
from custom_components.eedomus.const import DOMAIN


@pytest.mark.asyncio
async def test_async_migrate_entry_sequential(hass):
    """Teste la migration séquentielle complète d'une configuration de la version 1 à la version 4."""

    # 1. On initialise une fausse entrée en version 1 (simulant un ancien setup)
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        data={"host": "192.20.56.30"},
        options={},
    )
    config_entry.add_to_hass(hass)

    # 2. On patche le système de fichiers pour simuler la présence du fichier custom_mapping.yaml (étape 3->4)
    with patch("os.path.exists", return_value=True), patch("shutil.copy2") as mock_copy:
        # 3. Exécution de la fonction de migration
        result = await async_migrate_entry(hass, config_entry)

    # 4. Validations
    assert result is True, "La migration doit retourner True en cas de succès"

    # Vérification que la version finale de l'entrée est bien passée à 4
    # (Note : assurez-vous que la dernière étape de migration met bien à jour explicitement version=4)
    assert config_entry.version == 4

    # Vérification que les options par défaut ont bien été injectées lors des étapes 1->2 et 2->3
    assert config_entry.options.get("history") is not None
    assert config_entry.options.get("enable_api_proxy") is not None
