<?php
/**
 * Script PHP de fallback pour la gestion des valeurs non definies dans hass-eedomus.
 * 
 * Ce script appelle uniquement la fonction setValue de l'API eedomus.
 * Il est concu pour etre simple et direct, sans logique supplementaire.
 * 
 * Inspiration : https://github.com/2bprog/eedomus-domoticzevent-plugin/blob/master/php/2B_domzevents.php
 * 
 * @package hass-eedomus
 * @author Dan4Jer
 * @license MIT
 */

/**
 * Recupere un argument de requete (GET ou POST) avec validation.
 * 
 * @param string $name Nom de l'argument.
 * @param bool $required Indique si l'argument est obligatoire.
 * @param string|null $default Valeur par defaut si l'argument est optionnel.
 * @return string Valeur de l'argument.
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

// Recuperation des arguments
$value = getArg('value', true);
$device_id = getArg('device_id', true);
$api_host = getArg('api_host', true);
$api_user = getArg('api_user', true);
$api_secret = getArg('api_secret', true);
$log_enabled = getArg('log', false, 'false') === 'true';

if ($log_enabled) {
    error_log("[hass-eedomus PHP fallback] Script appele avec value=$value, device_id=$device_id, api_host=$api_host");
}

// Appel de la fonction setValue
try {
    // Construction de l'URL pour l'API locale eedomus
    $url = "http://$api_host/api/set?action=periph.value&periph_id=$device_id&value=$value&api_user=$api_user&api_secret=$api_secret";
    
    if ($log_enabled) {
        error_log("[hass-eedomus PHP fallback] Appel setValue: $url");
    }
    
    // Utilisation de file_get_contents pour un appel simple
    $response = @file_get_contents($url);
    
    if ($response === FALSE) {
        $error = error_get_last();
        http_response_code(500);
        echo "Erreur setValue: " . $error['message'];
        if ($log_enabled) {
            error_log("[hass-eedomus PHP fallback] Erreur setValue: " . $error['message']);
        }
        exit;
    }
    
    if ($log_enabled) {
        error_log("[hass-eedomus PHP fallback] Reponse setValue: $response");
    }
    
    // Retourner la reponse de l'API eedomus
    echo $response;
    
} catch (Exception $e) {
    http_response_code(500);
    echo "Erreur inattendue: " . $e->getMessage();
    if ($log_enabled) {
        error_log("[hass-eedomus PHP fallback] Erreur inattendue: " . $e->getMessage());
    }
}
