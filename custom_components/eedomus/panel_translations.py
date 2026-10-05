"""Panel translation catalog served by eedomus/get_translations (CAP-3).

EN is the source of truth (144 panel.* keys from the i18n inventory);
FR is its full translation. Texts carry raw {placeholder} tokens — the
panel performs the replacement client-side.
"""

from typing import Dict, Optional, Tuple

PANEL_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        # Shell / navigation
        "panel.common.title": "Eedomus Config",
        "panel.nav.aria": "Panel sections",
        "panel.tabs.peripheriques": "Peripherals",
        "panel.tabs.regles": "Rules",
        "panel.tabs.historique": "History",
        "panel.tabs.coherence": "Coherence",
        "panel.tabs.supervision": "Supervision",
        "panel.common.unknown_tab": "Unknown tab.",
        # Common (shared across tabs)
        "panel.common.retry": "Retry",
        "panel.common.command_refused": "command refused",
        "panel.common.unknown_error": "unknown error",
        "panel.common.no_entity": "no entity",
        "panel.common.unknown_date": "unknown date",
        "panel.common.unknown_value": "unknown",
        "panel.common.cancel": "Cancel",
        "panel.common.save": "Save",
        "panel.common.saving": "Saving…",
        "panel.common.applying": "Applying…",
        # Peripherals
        "panel.peripheriques.search.placeholder": "Search by name or usage_id",
        "panel.peripheriques.search.aria": ("Search a peripheral by name or usage_id"),
        "panel.peripheriques.filter.label": "Touched peripherals",
        "panel.peripheriques.filter.count": "({n})",
        "panel.peripheriques.status.total_one": "{n} peripheral",
        "panel.peripheriques.status.total_other": "{n} peripherals",
        "panel.peripheriques.status.filtered_one": (
            "— “Touched peripherals” filter active: {n} result"
        ),
        "panel.peripheriques.status.filtered_other": (
            "— “Touched peripherals” filter active: {n} results"
        ),
        "panel.peripheriques.error.load": "Failed to load peripherals: {err}.",
        "panel.peripheriques.empty": (
            "No peripheral detected. Check that the eedomus integration "
            "is configured."
        ),
        "panel.peripheriques.empty.search": (
            "No peripheral matches “{q}”. Clear the filter to restore " "the table."
        ),
        "panel.peripheriques.row.usage_id_label": "usage_id",
        "panel.peripheriques.row.usage_id_missing": "?",
        "panel.peripheriques.badge.label": "modified",
        "panel.peripheriques.badge.title": "Modified by {rule}, {date}",
        "panel.peripheriques.badge.aria": ("Modified by rule “{rule}”, {date}"),
        "panel.peripheriques.row.create_rule": ("Create a rule for this peripheral"),
        # Rules
        "panel.regles.error.load": "Failed to load the configuration: {err}.",
        "panel.regles.mode.aria": "Rule edit mode",
        "panel.regles.mode.form": "Form",
        "panel.regles.mode.yaml": "YAML",
        "panel.regles.prefill_note": "usage_id pre-filled: {id}",
        "panel.regles.create_rule": "Create a rule",
        "panel.regles.empty": "No mapping rule. The default mapping applies.",
        "panel.regles.row.usage_id_label": "usage_id",
        "panel.regles.row.edit": "Edit",
        "panel.regles.row.delete": "Delete",
        "panel.regles.row.delete_confirm": "Confirm deletion?",
        "panel.regles.form.usage_id": "usage_id",
        "panel.regles.form.usage_id_placeholder": "e.g. 7",
        "panel.regles.form.name": "Rule name",
        "panel.regles.form.name_placeholder": ("e.g. Living room temperature unit"),
        "panel.regles.form.ha_entity": "HA platform",
        "panel.regles.form.ha_subtype": "Device class",
        "panel.regles.form.ha_subtype_none": "(none)",
        "panel.regles.form.ha_subtype_hint": (
            "The class sets the applied device_class and unit "
            "(e.g. temperature → °C)."
        ),
        "panel.regles.yaml.aria": "Custom mapping YAML editor",
        "panel.regles.yaml.error_line": "line {n}: {msg}",
        "panel.regles.mode.announce": "Mode {mode}.",
        "panel.regles.mode.switch_refused": "switch refused: {msg}",
        "panel.regles.mode.switch_refused_generic": (
            "switch refused: fix the YAML errors or go back to the " "validated text"
        ),
        "panel.regles.validation.invalid": "invalid configuration",
        "panel.regles.validation.unavailable": "validation unavailable",
        "panel.regles.status.applied": "Configuration applied.",
        "panel.regles.status.rule_applied": (
            "Rule applied. {entity} is now in {unit}."
        ),
        "panel.regles.status.rule_applied_unit_fallback": "its new value",
        "panel.regles.status.rule_applied_entity_fallback": "usage_id {rule}",
        "panel.regles.status.save_failed": (
            "Save failed: {err}. The form keeps your changes."
        ),
        "panel.regles.status.deleted_entity": "rule {usageId}",
        "panel.regles.status.deleted_unit": "deleted",
        # History config
        "panel.historique.error.load": "Failed to load history: {err}.",
        "panel.historique.empty": (
            "No backup yet. The first save will archive the current " "version."
        ),
        "panel.historique.current.title": "Current configuration",
        "panel.historique.current.badge": "current",
        "panel.historique.current.meta": "in effect",
        "panel.historique.version.title": "Version of {timestamp}",
        "panel.historique.reason.ingestion": "manual file edit",
        "panel.historique.reason.migration": "schema migration",
        "panel.historique.reason.panel": "save from the panel",
        "panel.historique.restore.action": "Restore",
        "panel.historique.restore.confirm": "Confirm restore?",
        "panel.historique.restore.confirm_message": (
            "Restore the version of {ts}? The current mapping will be " "archived."
        ),
        "panel.historique.diff.first_version": (
            "First version — the diff will appear after the next save."
        ),
        "panel.historique.restore.progress": "Saving… then Applying…",
        "panel.historique.diff.line_added": "line added",
        "panel.historique.diff.line_removed": "line removed",
        "panel.historique.diff.line_modified": "line changed",
        "panel.historique.diff.region_aria": ("Differences with the previous version"),
        "panel.historique.restore.success": (
            "Version of {ts} restored. The replaced mapping is archived."
        ),
        "panel.historique.restore.failed": (
            "Restore failed. The current mapping is kept."
        ),
        # Coherence
        "panel.coherence.search.placeholder": "Search by name or periph_id",
        "panel.coherence.search.aria": ("Search a peripheral by name or periph_id"),
        "panel.coherence.filter.label": "To verify",
        "panel.coherence.filter.count": "({n})",
        "panel.coherence.status.total_one": "{n} peripheral",
        "panel.coherence.status.total_other": "{n} peripherals",
        "panel.coherence.status.filtered_one": (
            "— “To verify” view active: {n} result"
        ),
        "panel.coherence.status.filtered_other": (
            "— “To verify” view active: {n} results"
        ),
        "panel.coherence.status.no_result": ("No peripheral matches “{q}”."),
        "panel.coherence.status.all_clear": (
            "Everything is consistent. No peripheral to check."
        ),
        "panel.coherence.table.caption": ("Eedomus peripheral mapping coherence"),
        "panel.coherence.columns.periph_id": "periph_id",
        "panel.coherence.columns.name": "Name",
        "panel.coherence.columns.entity_id": "HA entity",
        "panel.coherence.columns.type": "Type / subtype",
        "panel.coherence.columns.status": "Status",
        "panel.coherence.cell_labels.periph_id": "Peripheral",
        "panel.coherence.sort.aria": "Sort by {label}",
        "panel.coherence.sort.aria_asc": ", currently ascending",
        "panel.coherence.sort.aria_desc": ", currently descending",
        "panel.coherence.chips.sans_entite": "no HA entity",
        "panel.coherence.chips.douteux": "doubtful mapping",
        "panel.coherence.chips.regle_active": "active rule",
        "panel.coherence.chips.en_erreur": "import retrying",
        "panel.coherence.chips.coherent": "consistent",
        "panel.coherence.chips.unknown": "{raw}",
        "panel.coherence.chips.en_erreur_detail": "import retrying: {truncated}",
        "panel.coherence.chips.error_title": "{msg}",
        "panel.coherence.entity_link.aria": ("View {entity_id} in Home Assistant"),
        "panel.coherence.trigger.aria": "Details of peripheral {periph_id}",
        "panel.coherence.trigger.popover.aria": (
            "Peripheral detail {name} ({periph_id})"
        ),
        "panel.coherence.detail.section_live": "Living state",
        "panel.coherence.detail.section_identity": "Mapping identity",
        "panel.coherence.detail.error_message": "{error_message}",
        "panel.coherence.detail.retry_after": "— retry at {retry_after}",
        "panel.coherence.detail.attempts_one": "({n} attempt)",
        "panel.coherence.detail.attempts_other": "({n} attempts)",
        "panel.coherence.detail.entity_id": "HA entity",
        "panel.coherence.detail.current_value": "Current value",
        "panel.coherence.detail.usage_id": "usage_id",
        "panel.coherence.detail.parent": "Parent peripheral",
        "panel.coherence.detail.last_update": "Last update",
        "panel.coherence.detail.ha_entity": "ha_entity",
        "panel.coherence.detail.ha_subtype": "ha_subtype",
        "panel.coherence.detail.justification": "Justification",
        "panel.coherence.detail.view_in_ha": "View in HA",
        "panel.coherence.detail.create_rule": "Create a rule",
        "panel.coherence.detail.raw_summary": "Raw fields from the eedomus API",
        "panel.coherence.detail.copy_json": "Copy JSON",
        "panel.coherence.detail.copy_feedback": "JSON copied.",
        "panel.coherence.detail.copy_failed": "Copy failed.",
        "panel.coherence.error.load": "Failed to load coherence: {err}.",
        "panel.coherence.empty": (
            "No peripheral detected. Check that the eedomus box is "
            "reachable and the integration is configured."
        ),
        "panel.coherence.empty.search": (
            "No peripheral matches “{q}”. Clear the filter to restore " "the table."
        ),
        "panel.coherence.empty.all_clear": (
            "Everything is consistent. No peripheral to check."
        ),
        "panel.coherence.empty.show_all": "Show all",
        "panel.coherence.skeleton.aria": "Loading coherence…",
        # Supervision
        "panel.supervision.box.title": "Box {name}",
        "panel.supervision.box.fallback": "Box #{n}",
        "panel.supervision.cycles": "Over the last {n} refresh cycles.",
        "panel.supervision.card.refresh_time": "Refresh time",
        "panel.supervision.card.periphs": "Peripherals",
        "panel.supervision.card.api_calls": "API calls",
        "panel.supervision.value.refresh_time": (
            "Last cycle: {n} s total, {api} s on the API."
        ),
        "panel.supervision.value.periphs": (
            "{total} peripherals, {dynamic} dynamic."
        ),
        "panel.supervision.value.api_calls": (
            "{n} calls to the eedomus API during the last cycle."
        ),
        "panel.supervision.link.coherence": "See the coherence table",
        "panel.supervision.error.load": "Failed to load metrics: {err}.",
        "panel.supervision.empty": (
            "No refresh cycle recorded yet. The charts fill in after "
            "the first refresh."
        ),
        "panel.supervision.skeleton.aria": "Loading supervision…",
    },
    "fr": {
        # Shell / navigation
        "panel.common.title": "Eedomus Config",
        "panel.nav.aria": "Sections du panneau",
        "panel.tabs.peripheriques": "Périphériques",
        "panel.tabs.regles": "Règles",
        "panel.tabs.historique": "Historique config",
        "panel.tabs.coherence": "Cohérence",
        "panel.tabs.supervision": "Supervision",
        "panel.common.unknown_tab": "Onglet inconnu.",
        # Common (shared across tabs)
        "panel.common.retry": "Réessayer",
        "panel.common.command_refused": "commande refusée",
        "panel.common.unknown_error": "erreur inconnue",
        "panel.common.no_entity": "aucune entité",
        "panel.common.unknown_date": "date inconnue",
        "panel.common.unknown_value": "inconnu",
        "panel.common.cancel": "Annuler",
        "panel.common.save": "Enregistrer",
        "panel.common.saving": "Sauvegarde…",
        "panel.common.applying": "Application…",
        # Peripherals
        "panel.peripheriques.search.placeholder": ("Rechercher par nom ou usage_id"),
        "panel.peripheriques.search.aria": (
            "Rechercher un périphérique par nom ou usage_id"
        ),
        "panel.peripheriques.filter.label": "Périphériques touchés",
        "panel.peripheriques.filter.count": "({n})",
        "panel.peripheriques.status.total_one": "{n} périphérique",
        "panel.peripheriques.status.total_other": "{n} périphériques",
        "panel.peripheriques.status.filtered_one": (
            "— filtre « Périphériques touchés » actif : {n} résultat"
        ),
        "panel.peripheriques.status.filtered_other": (
            "— filtre « Périphériques touchés » actif : {n} résultats"
        ),
        "panel.peripheriques.error.load": (
            "Impossible de charger les périphériques : {err}."
        ),
        "panel.peripheriques.empty": (
            "Aucun périphérique détecté. Vérifiez que l'intégration "
            "eedomus est configurée."
        ),
        "panel.peripheriques.empty.search": (
            "Aucun périphérique ne correspond à “{q}”. Effacez le filtre "
            "pour restituer la table."
        ),
        "panel.peripheriques.row.usage_id_label": "usage_id",
        "panel.peripheriques.row.usage_id_missing": "?",
        "panel.peripheriques.badge.label": "modifié",
        "panel.peripheriques.badge.title": "Modifié par {rule}, {date}",
        "panel.peripheriques.badge.aria": ("Modifié par la règle « {rule} », {date}"),
        "panel.peripheriques.row.create_rule": ("Créer une règle pour ce périphérique"),
        # Rules
        "panel.regles.error.load": ("Impossible de charger la configuration : {err}."),
        "panel.regles.mode.aria": "Mode d'édition des règles",
        "panel.regles.mode.form": "Formulaire",
        "panel.regles.mode.yaml": "YAML",
        "panel.regles.prefill_note": "usage_id pré-rempli : {id}",
        "panel.regles.create_rule": "Créer une règle",
        "panel.regles.empty": (
            "Aucune règle de mapping. Le mapping par défaut s'applique."
        ),
        "panel.regles.row.usage_id_label": "usage_id",
        "panel.regles.row.edit": "Modifier",
        "panel.regles.row.delete": "Supprimer",
        "panel.regles.row.delete_confirm": "Confirmer la suppression ?",
        "panel.regles.form.usage_id": "usage_id",
        "panel.regles.form.usage_id_placeholder": "ex. 7",
        "panel.regles.form.name": "Nom de la règle",
        "panel.regles.form.name_placeholder": "ex. Unité température salon",
        "panel.regles.form.ha_entity": "Plateforme HA",
        "panel.regles.form.ha_subtype": "Classe de périphérique",
        "panel.regles.form.ha_subtype_none": "(aucune)",
        "panel.regles.form.ha_subtype_hint": (
            "La classe détermine device_class et unité appliquées "
            "(ex. temperature → °C)."
        ),
        "panel.regles.yaml.aria": "Éditeur YAML du mapping custom",
        "panel.regles.yaml.error_line": "ligne {n} : {msg}",
        "panel.regles.mode.announce": "Mode {mode}.",
        "panel.regles.mode.switch_refused": "bascule refusée : {msg}",
        "panel.regles.mode.switch_refused_generic": (
            "bascule refusée : corrigez les erreurs YAML ou revenez au " "texte validé"
        ),
        "panel.regles.validation.invalid": "configuration invalide",
        "panel.regles.validation.unavailable": "validation impossible",
        "panel.regles.status.applied": "Configuration appliquée.",
        "panel.regles.status.rule_applied": (
            "Règle appliquée. {entity} est maintenant en {unit}."
        ),
        "panel.regles.status.rule_applied_unit_fallback": "sa nouvelle valeur",
        "panel.regles.status.rule_applied_entity_fallback": "usage_id {rule}",
        "panel.regles.status.save_failed": (
            "Échec de la sauvegarde : {err}. Le formulaire conserve vos "
            "modifications."
        ),
        "panel.regles.status.deleted_entity": "règle {usageId}",
        "panel.regles.status.deleted_unit": "supprimée",
        # History config
        "panel.historique.error.load": ("Impossible de charger l'historique : {err}."),
        "panel.historique.empty": (
            "Aucune sauvegarde encore. La première sauvegarde archivera "
            "la version courante."
        ),
        "panel.historique.current.title": "Configuration actuelle",
        "panel.historique.current.badge": "actuelle",
        "panel.historique.current.meta": "en vigueur",
        "panel.historique.version.title": "Version du {timestamp}",
        "panel.historique.reason.ingestion": "édition manuelle du fichier",
        "panel.historique.reason.migration": "migration de schéma",
        "panel.historique.reason.panel": "sauvegarde depuis le panneau",
        "panel.historique.restore.action": "Restaurer",
        "panel.historique.restore.confirm": "Confirmer la restauration ?",
        "panel.historique.restore.confirm_message": (
            "Restaurer la version du {ts} ? Le mapping actuel sera " "archivé."
        ),
        "panel.historique.diff.first_version": (
            "Première version — le diff apparaîtra à la prochaine " "sauvegarde."
        ),
        "panel.historique.restore.progress": "Sauvegarde… puis Application…",
        "panel.historique.diff.line_added": "ligne ajoutée",
        "panel.historique.diff.line_removed": "ligne supprimée",
        "panel.historique.diff.line_modified": "ligne modifiée",
        "panel.historique.diff.region_aria": ("Différences avec la version précédente"),
        "panel.historique.restore.success": (
            "Version du {ts} restaurée. Le mapping remplacé est archivé."
        ),
        "panel.historique.restore.failed": (
            "Échec de la restauration. Le mapping courant est conservé."
        ),
        # Coherence
        "panel.coherence.search.placeholder": ("Rechercher par nom ou periph_id"),
        "panel.coherence.search.aria": (
            "Rechercher un périphérique par nom ou periph_id"
        ),
        "panel.coherence.filter.label": "À vérifier",
        "panel.coherence.filter.count": "({n})",
        "panel.coherence.status.total_one": "{n} périphérique",
        "panel.coherence.status.total_other": "{n} périphériques",
        "panel.coherence.status.filtered_one": (
            "— vue « À vérifier » active : {n} résultat"
        ),
        "panel.coherence.status.filtered_other": (
            "— vue « À vérifier » active : {n} résultats"
        ),
        "panel.coherence.status.no_result": (
            "Aucun périphérique ne correspond à “{q}”."
        ),
        "panel.coherence.status.all_clear": (
            "Tout est cohérent. Aucun périphérique à vérifier."
        ),
        "panel.coherence.table.caption": (
            "Cohérence du mapping des périphériques eedomus"
        ),
        "panel.coherence.columns.periph_id": "periph_id",
        "panel.coherence.columns.name": "Nom",
        "panel.coherence.columns.entity_id": "Entité HA",
        "panel.coherence.columns.type": "Type / sous-type",
        "panel.coherence.columns.status": "Statut",
        "panel.coherence.cell_labels.periph_id": "Périphérique",
        "panel.coherence.sort.aria": "Trier par {label}",
        "panel.coherence.sort.aria_asc": ", actuellement croissant",
        "panel.coherence.sort.aria_desc": ", actuellement décroissant",
        "panel.coherence.chips.sans_entite": "sans entité HA",
        "panel.coherence.chips.douteux": "mapping douteux",
        "panel.coherence.chips.regle_active": "règle active",
        "panel.coherence.chips.en_erreur": "import en reprise",
        "panel.coherence.chips.coherent": "cohérent",
        "panel.coherence.chips.unknown": "{raw}",
        "panel.coherence.chips.en_erreur_detail": "import en reprise : {truncated}",
        "panel.coherence.chips.error_title": "{msg}",
        "panel.coherence.entity_link.aria": ("Voir {entity_id} dans Home Assistant"),
        "panel.coherence.trigger.aria": ("Détails du périphérique {periph_id}"),
        "panel.coherence.trigger.popover.aria": (
            "Détail du périphérique {name} ({periph_id})"
        ),
        "panel.coherence.detail.section_live": "État vivant",
        "panel.coherence.detail.section_identity": "Identité de mapping",
        "panel.coherence.detail.error_message": "{error_message}",
        "panel.coherence.detail.retry_after": ("— nouvelle tentative {retry_after}"),
        "panel.coherence.detail.attempts_one": "({n} tentative)",
        "panel.coherence.detail.attempts_other": "({n} tentatives)",
        "panel.coherence.detail.entity_id": "Entité HA",
        "panel.coherence.detail.current_value": "Valeur courante",
        "panel.coherence.detail.usage_id": "usage_id",
        "panel.coherence.detail.parent": "Périphérique parent",
        "panel.coherence.detail.last_update": "Dernière mise à jour",
        "panel.coherence.detail.ha_entity": "ha_entity",
        "panel.coherence.detail.ha_subtype": "ha_subtype",
        "panel.coherence.detail.justification": "Justification",
        "panel.coherence.detail.view_in_ha": "Voir dans HA",
        "panel.coherence.detail.create_rule": "Créer une règle",
        "panel.coherence.detail.raw_summary": "Champs bruts de l'API eedomus",
        "panel.coherence.detail.copy_json": "Copier le JSON",
        "panel.coherence.detail.copy_feedback": "JSON copié.",
        "panel.coherence.detail.copy_failed": "Copie impossible.",
        "panel.coherence.error.load": ("Impossible de charger la cohérence : {err}."),
        "panel.coherence.empty": (
            "Aucun périphérique détecté. Vérifiez que la box eedomus est "
            "joignable et que l'intégration est configurée."
        ),
        "panel.coherence.empty.search": (
            "Aucun périphérique ne correspond à “{q}”. Effacez le filtre "
            "pour restituer la table."
        ),
        "panel.coherence.empty.all_clear": (
            "Tout est cohérent. Aucun périphérique à vérifier."
        ),
        "panel.coherence.empty.show_all": "Tout afficher",
        "panel.coherence.skeleton.aria": "Chargement de la cohérence…",
        # Supervision
        "panel.supervision.box.title": "Box {name}",
        "panel.supervision.box.fallback": "Box #{n}",
        "panel.supervision.cycles": "Sur les {n} derniers cycles de refresh.",
        "panel.supervision.card.refresh_time": "Temps de refresh",
        "panel.supervision.card.periphs": "Périphériques",
        "panel.supervision.card.api_calls": "Appels API",
        "panel.supervision.value.refresh_time": (
            "Dernier cycle : {n} s au total, {api} s sur l'API."
        ),
        "panel.supervision.value.periphs": (
            "{total} périphériques, dont {dynamic} dynamiques."
        ),
        "panel.supervision.value.api_calls": (
            "{n} appels à l'API eedomus lors du dernier cycle."
        ),
        "panel.supervision.link.coherence": "Voir le tableau de cohérence",
        "panel.supervision.error.load": (
            "Impossible de charger les métriques : {err}."
        ),
        "panel.supervision.empty": (
            "Aucun cycle de refresh enregistré pour l'instant. Les "
            "graphiques se rempliront après le premier refresh."
        ),
        "panel.supervision.skeleton.aria": "Chargement de la supervision…",
    },
}


def get_panel_translations(locale: Optional[str]) -> Tuple[str, Dict[str, str]]:
    """Resolve a locale into (locale, flat key -> text) catalog.

    The requested locale is served when covered; an unknown or absent
    locale falls back to English, never an error. Within a covered
    locale, any key missing from the translation keeps the English
    source text, so a partial catalog never renders an empty string.
    """
    english = PANEL_TRANSLATIONS["en"]
    base = ""
    if isinstance(locale, str):
        base = locale.strip().lower().replace("_", "-").split("-", 1)[0]
    catalog = PANEL_TRANSLATIONS.get(base)
    if catalog is None:
        return "en", dict(english)
    resolved = dict(english)
    resolved.update(catalog)
    return base, resolved
