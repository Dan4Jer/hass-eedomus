#!/bin/bash

# Script pour activer l'option history dans l'intégration eedomus
# Ce script doit être exécuté sur le Raspberry Pi

set -e

echo "🔧 Activation de l'option history pour l'intégration eedomus..."
echo "=================================================================="

# Vérifier si nous sommes sur le Raspberry Pi
if [ ! -d "/config/.storage" ]; then
    echo "❌ Erreur: Ce script doit être exécuté sur le Raspberry Pi"
    echo "   Le répertoire /config/.storage n'a pas été trouvé"
    exit 1
fi

# Trouver le fichier de stockage eedomus
STORAGE_FILE=$(find /config/.storage -name "*eedomus*" -type f 2>/dev/null | head -1)

if [ -z "$STORAGE_FILE" ]; then
    echo "❌ Erreur: Aucun fichier de stockage eedomus trouvé"
    echo "   Vérifiez que l'intégration eedomus est bien installée"
    exit 1
fi

echo "✅ Fichier de stockage trouvé: $STORAGE_FILE"

# Lire le fichier JSON
CONTENT=$(cat "$STORAGE_FILE")

# Vérifier si l'option history existe
if echo "$CONTENT" | grep -q '"history"'; then
    echo "ℹ️  L'option history existe déjà dans la configuration"
    
    # Vérifier si elle est activée
    if echo "$CONTENT" | grep -q '"history": true'; then
        echo "✅ L'option history est déjà activée"
        exit 0
    else
        echo "⚠️  L'option history existe mais est désactivée"
        echo "   Activation en cours..."
        
        # Remplacer history: false par history: true
        CONTENT=$(echo "$CONTENT" | sed 's/"history": false/"history": true/g')
        echo "$CONTENT" > "$STORAGE_FILE"
        echo "✅ Option history activée avec succès"
        exit 0
    fi
else
    echo "⚠️  L'option history n'existe pas dans la configuration"
    echo "   Ajout de l'option..."
    
    # Ajouter l'option history
    CONTENT=$(echo "$CONTENT" | sed 's/"options": {/"options": {"history": true, /')
    echo "$CONTENT" > "$STORAGE_FILE"
    echo "✅ Option history ajoutée et activée avec succès"
    exit 0
fi

echo "❓ État inconnu - vérifiez manuellement le fichier: $STORAGE_FILE"
exit 1
