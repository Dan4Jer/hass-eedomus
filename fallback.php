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
$value = $_GET['value'];
$device_id = $_GET['device_id'];

// Appel de la fonction setValue de l'API eedomus
$result = setValue($device_id, $value);

// Retourner le resultat directement (setValue retourne déjà un JSON valide)
if ($result !== false) {
    echo $result;
} else {
    echo '{"success": 0, "error": "Erreur lors de l\'appel a setValue"}';
}
