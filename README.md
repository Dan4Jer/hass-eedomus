# eedomus custom component


Copier le contenu dans `/config/custom_components/eedomus/` puis redémarrer Home Assistant.
Ensuite, aller dans Configuration -> Intégrations -> Ajouter -> eedomus, renseigner :
- Host (IP ou host)
- Api User
- Api Secret


L'intégration utilise `DataUpdateCoordinator` et récupère les devices toutes les `SCAN_INTERVAL` secondes.


Pour les commandes, la plateforme `switch` appelle l'API eedomus via `client.async_set()`.


Tests:
- Vérifier que les sensors apparaissent
- Forcer un `coordinator.async_request_refresh()` dans les logs
