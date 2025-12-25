<?php
/**
 * Script PHP de fallback pour la gestion des valeurs non definies dans hass-eedomus.
 * 
 * Ce script simplifie effectue directement un setvalue sur l'API eedomus locale
 * lorsqu'une valeur est rejetee. Il utilise les memes parametres que l'API standard.
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

/**
 * Effectue un appel a l'API eedomus locale pour setter une valeur.
 * 
 * @param string $api_host Adresse IP de la box eedomus.
 * @param string $device_id ID du peripherique.
 * @param string $value Valeur a setter.
 * @param string $api_user Utilisateur API.
 * @param string $api_secret Cle secrete API.
 * @param bool $log_enabled Active la journalisation.
 * @return string Resultat de l'appel API.
 */
function callEedomusAPI(string $api_host, string $device_id, string $value, 
                        string $api_user, string $api_secret, bool $log_enabled): string {
    // Construction de l'URL pour l'API locale eedomus
    $url = "http://$api_host/api/set?action=periph.value&periph_id=$device_id&value=$value&api_user=$api_user&api_secret=$api_secret";
    
    if ($log_enabled) {
        error_log("[hass-eedomus fallback] Appel API eedomus: $url");
    }
    
    // Initialisation de cURL
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    
    // Execution de la requete
    $response = curl_exec($ch);
    
    if (curl_errno($ch)) {
        $error = curl_error($ch);
        curl_close($ch);
        if ($log_enabled) {
            error_log("[hass-eedomus fallback] Erreur cURL: $error");
        }
        http_response_code(500);
        echo "Erreur cURL: $error";
        exit;
    }
    
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($log_enabled) {
        error_log("[hass-eedomus fallback] Reponse API: HTTP $http_code - $response");
    }
    
    if ($http_code != 200) {
        http_response_code($http_code);
        echo "Erreur API eedomus: HTTP $http_code - $response";
        exit;
    }
    
    return $response;
}

// Recuperation des arguments
$value = getArg('value', true);
$device_id = getArg('device_id', true);
$api_host = getArg('api_host', true);
$api_user = getArg('api_user', true);
$api_secret = getArg('api_secret', true);
$log_enabled = getArg('log', false, 'false') === 'true';

if ($log_enabled) {
    error_log("[hass-eedomus fallback] Script appele avec value=$value, device_id=$device_id, api_host=$api_host");
}

// Appel direct a l'API eedomus pour setter la valeur
try {
    $response = callEedomusAPI($api_host, $device_id, $value, $api_user, $api_secret, $log_enabled);
    
    // Retourner la reponse de l'API eedomus
    echo $response;
    
} catch (Exception $e) {
    http_response_code(500);
    echo "Erreur inattendue: " . $e->getMessage();
    if ($log_enabled) {
        error_log("[hass-eedomus fallback] Erreur inattendue: " . $e->getMessage());
    }
}
