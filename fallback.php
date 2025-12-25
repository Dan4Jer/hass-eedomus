<?php
/**
 * Script PHP de fallback pour la gestion des valeurs non définies dans hass-eedomus.
 * 
 * Ce script permet de transformer ou mapper une valeur rejetée par l'API eedomus
 * avant une nouvelle tentative d'envoi. Il offre une solution flexible et configurable
 * pour gérer les valeurs non autorisées ou invalides.
 * 
 * @package hass-eedomus
 * @author Dan4Jer
 * @license MIT
 */

/**
 * Récupère un argument de requête (GET ou POST) avec validation.
 * 
 * @param string $name Nom de l'argument.
 * @param bool $required Indique si l'argument est obligatoire.
 * @param string|null $default Valeur par défaut si l'argument est optionnel.
 * @return string Valeur de l'argument.
 * @throws InvalidArgumentException Si l'argument est manquant ou invalide.
 */
function getArg(string $name, bool $required = false, ?string $default = null): string {
    $value = isset($_GET[$name]) ? $_GET[$name] : (isset($_POST[$name]) ? $_POST[$name] : $default);
    
    if ($required && ($value === null || $value === '')) {
        http_response_code(400);
        echo "Argument manquant ou invalide : $name";
        exit;
    }
    
    return htmlspecialchars($value, ENT_QUOTES, 'UTF-8');
}

/**
 * Journalise un message si la journalisation est activée.
 * 
 * @param string $message Message à journaliser.
 * @param bool $log_enabled Indique si la journalisation est activée.
 */
function logMessage(string $message, bool $log_enabled): void {
    if ($log_enabled) {
        error_log("[hass-eedomus fallback] " . $message);
    }
}

// Récupération des arguments
$value = getArg('value', true);
$device_id = getArg('device_id', true);
$cmd_name = getArg('cmd_name', true);
$log_enabled = getArg('log', false, 'false') === 'true';

logMessage("Script appelé avec value=$value, device_id=$device_id, cmd_name=$cmd_name", $log_enabled);

// Exemple de mapping des valeurs
// Personnalisez cette section selon vos besoins
$mapping = [
    'haut' => '100',
    'bas' => '0',
    'on' => '1',
    'off' => '0',
    'open' => '1',
    'close' => '0',
];

// Vérification si la valeur est dans le mapping
if (array_key_exists($value, $mapping)) {
    $new_value = $mapping[$value];
    logMessage("Valeur mappée : $value -> $new_value", $log_enabled);
    echo $new_value;
    exit;
}

// Si la valeur n'est pas dans le mapping, essayer de la convertir en nombre
if (is_numeric($value)) {
    $numeric_value = floatval($value);
    // Exemple de traitement conditionnel : limiter à une plage de valeurs
    $min_value = 0;
    $max_value = 100;
    $new_value = max($min_value, min($max_value, $numeric_value));
    logMessage("Valeur numérique ajustée : $value -> $new_value", $log_enabled);
    echo $new_value;
    exit;
}

// Si aucune transformation n'est possible, retourner une erreur
http_response_code(400);
echo "Valeur non valide ou non mappée : $value";
logMessage("Erreur : Valeur non valide ou non mappée : $value", $log_enabled);
