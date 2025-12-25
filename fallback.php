<?php
/**
 * Script PHP de fallback pour la gestion des valeurs non definies dans hass-eedomus.
 * 
 * Ce script appelle uniquement la fonction setValue de l'API eedomus.
 * Il est concu pour etre simple et direct, sans logique supplementaire.
 * 
 * Documentation : https://doc.eedomus.com/view/Scripts
 * 
 * @package hass-eedomus
 * @author Dan4Jer
 * @license MIT
 */

// Recuperation des arguments minimaux
$value = isset($_GET['value']) ? $_GET['value'] : (isset($_POST['value']) ? $_POST['value'] : '');
$device_id = isset($_GET['device_id']) ? $_GET['device_id'] : (isset($_POST['device_id']) ? $_POST['device_id'] : '');

// Appel de la fonction setValue de l'API eedomus
try {
    // Appel de la fonction setValue avec les parametres minimaux
    $result = setValue($device_id, $value);
    
    // Retourner le resultat
    echo json_encode(array("success" => 1, "result" => $result));
    
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(array("success" => 0, "error" => $e->getMessage()));
}
