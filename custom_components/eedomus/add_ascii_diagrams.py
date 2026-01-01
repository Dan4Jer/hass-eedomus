#!/usr/bin/env python3
"""
Script pour ajouter des schémas ASCII avant chaque diagramme Mermaid dans le README.md
"""

import re

def add_ascii_diagrams():
    """Ajouter des schémas ASCII avant les diagrammes Mermaid"""
    
    with open('README.md', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern pour trouver les blocs mermaid
    pattern = r'(```mermaid\n)'
    
    # Dictionnaire de schémas ASCII pour chaque type de diagramme
    ascii_diagrams = {
        1: """
+---------------------+       HTTP       +---------------------+
|                     |  -------------->  |                     |
|   Home Assistant    |                   |   Eedomus Box       |
|                     |  <--------------  |                     |
+---------------------+       Webhook     +---------------------+
            Core                          API Endpoint
              |                                |
              v                                v
        Eedomus Client                    Devices Manager
        """,
        2: """
+---------------------+       HTTP       +---------------------+
|                     |  -------------->  |                     |
|   Home Assistant    |                   |   Eedomus Box       |
|                     |                   |                     |
+---------------------+                   +---------------------+
            API Proxy                         API Endpoint
              |                                |
              v                                v
        Webhook Receiver                  Devices Manager
        """,
        3: """
+---------------------+       HTTP       +---------------------+
|                     |  -------------->  |                     |
|   Home Assistant    |                   |   Eedomus Box       |
|                     |  <--------------  |                     |
+---------------------+       Webhook     +---------------------+
            Core                          API Endpoint
              |                                |
              v                                v
        Eedomus Client                    Devices Manager
        API Proxy
        """,
        4: """
+---------------------+       +---------------------+
|   Home Assistant    |       |   Eedomus Box       |
|                     |       |                     |
|   +-------------+   |       |   +-------------+   |
|   |  Light      |   |       |   |  Light      |   |
|   +-------------+   |       |   +-------------+   |
|   |  Switch     |   |       |   |  Switch     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Cover      |   |       |   |  Cover      |   |
|   +-------------+   |       |   +-------------+   |
|   |  Sensor     |   |       |   |  Sensor     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Binary     |   |       |   |  Binary     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Select     |   |       |   |  Select     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Climate    |   |       |   |  Climate    |   |
|   +-------------+   |       |   +-------------+   |
+---------------------+       +---------------------+
        Mapping System              Device Data
        """,
        5: """
+---------------------+       +---------------------+
|   Home Assistant    |       |   Eedomus Box       |
|                     |       |                     |
|   RGBW Light        |       |   RGBW Light        |
|   +-------------+   |       |   +-------------+   |
|   |  Red        |   |       |   |  Red        |   |
|   |  Green      |   |       |   |  Green      |   |
|   |  Blue       |   |       |   |  Blue       |   |
|   |  White      |   |       |   |  White      |   |
|   |  Consumption|   |       |   |  Consumption|   |
|   |  Color Preset|   |       |   |  Color Preset|   |
|   +-------------+   |       |   +-------------+   |
+---------------------+       +---------------------+
        Parent Device              Child Devices
        """,
        6: """
+---------------------+       +---------------------+
|   Home Assistant    |       |   Eedomus Box       |
|                     |       |                     |
|   Thermostat        |       |   Thermostat        |
|   +-------------+   |       |   +-------------+   |
|   |  Setpoint   |   |       |   |  Setpoint   |   |
|   +-------------+   |       |   +-------------+   |
|   |  Temperature|   |       |   |  Temperature|   |
|   +-------------+   |       |   +-------------+   |
+---------------------+       +---------------------+
        Setpoint Device           Temperature Sensor
        """,
        7: """
+---------------------+       +---------------------+
|   Home Assistant    |       |   Eedomus Box       |
|                     |       |                     |
|   +-------------+   |       |   +-------------+   |
|   |  Light      |   |       |   |  Light      |   |
|   +-------------+   |       |   +-------------+   |
|   |  Switch     |   |       |   |  Switch     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Cover      |   |       |   |  Cover      |   |
|   +-------------+   |       |   +-------------+   |
|   |  Sensor     |   |       |   |  Sensor     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Binary     |   |       |   |  Binary     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Select     |   |       |   |  Select     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Climate    |   |       |   |  Climate    |   |
|   +-------------+   |       |   +-------------+   |
|   |  Battery    |   |       |   |  Battery    |   |
|   +-------------+   |       |   +-------------+   |
+---------------------+       +---------------------+
        HA Entities                Eedomus Data
        """,
        8: """
+---------------------+       +---------------------+
|   Home Assistant    |       |   Eedomus Box       |
|                     |       |                     |
|   +-------------+   |       |   +-------------+   |
|   |  Light      |   |       |   |  Light      |   |
|   +-------------+   |       |   +-------------+   |
|   |  Switch     |   |       |   |  Switch     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Cover      |   |       |   |  Cover      |   |
|   +-------------+   |       |   +-------------+   |
|   |  Sensor     |   |       |   |  Sensor     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Binary     |   |       |   |  Binary     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Select     |   |       |   |  Select     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Climate    |   |       |   |  Climate    |   |
|   +-------------+   |       |   +-------------+   |
|   |  Battery    |   |       |   |  Battery    |   |
|   +-------------+   |       |   +-------------+   |
+---------------------+       +---------------------+
        Mapping System              Device Data
        """,
        9: """
+---------------------+       +---------------------+
|   Home Assistant    |       |   Eedomus Box       |
|                     |       |                     |
|   +-------------+   |       |   +-------------+   |
|   |  Light      |   |       |   |  Light      |   |
|   +-------------+   |       |   +-------------+   |
|   |  Switch     |   |       |   |  Switch     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Cover      |   |       |   |  Cover      |   |
|   +-------------+   |       |   +-------------+   |
|   |  Sensor     |   |       |   |  Sensor     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Binary     |   |       |   |  Binary     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Select     |   |       |   |  Select     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Climate    |   |       |   |  Climate    |   |
|   +-------------+   |       |   +-------------+   |
|   |  Battery    |   |       |   |  Battery    |   |
|   +-------------+   |       |   +-------------+   |
+---------------------+       +---------------------+
        Data Flow                  Data Flow
        """,
        10: """
+---------------------+       +---------------------+
|   Home Assistant    |       |   Eedomus Box       |
|                     |       |                     |
|   +-------------+   |       |   +-------------+   |
|   |  Light      |   |       |   |  Light      |   |
|   +-------------+   |       |   +-------------+   |
|   |  Switch     |   |       |   |  Switch     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Cover      |   |       |   |  Cover      |   |
|   +-------------+   |       |   +-------------+   |
|   |  Sensor     |   |       |   |  Sensor     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Binary     |   |       |   |  Binary     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Select     |   |       |   |  Select     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Climate    |   |       |   |  Climate    |   |
|   +-------------+   |       |   +-------------+   |
|   |  Battery    |   |       |   |  Battery    |   |
|   +-------------+   |       |   +-------------+   |
+---------------------+       +---------------------+
        Legend                      Legend
        """,
        11: """
+---------------------+       +---------------------+
|   Home Assistant    |       |   Eedomus Box       |
|                     |       |                     |
|   +-------------+   |       |   +-------------+   |
|   |  Light      |   |       |   |  Light      |   |
|   +-------------+   |       |   +-------------+   |
|   |  Switch     |   |       |   |  Switch     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Cover      |   |       |   |  Cover      |   |
|   +-------------+   |       |   +-------------+   |
|   |  Sensor     |   |       |   |  Sensor     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Binary     |   |       |   |  Binary     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Select     |   |       |   |  Select     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Climate    |   |       |   |  Climate    |   |
|   +-------------+   |       |   +-------------+   |
|   |  Battery    |   |       |   |  Battery    |   |
|   +-------------+   |       |   +-------------+   |
+---------------------+       +---------------------+
        Git Graph                   Git Graph
        """,
        12: """
+---------------------+       +---------------------+
|   Home Assistant    |       |   Eedomus Box       |
|                     |       |                     |
|   +-------------+   |       |   +-------------+   |
|   |  Light      |   |       |   |  Light      |   |
|   +-------------+   |       |   +-------------+   |
|   |  Switch     |   |       |   |  Switch     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Cover      |   |       |   |  Cover      |   |
|   +-------------+   |       |   +-------------+   |
|   |  Sensor     |   |       |   |  Sensor     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Binary     |   |       |   |  Binary     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Select     |   |       |   |  Select     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Climate    |   |       |   |  Climate    |   |
|   +-------------+   |       |   +-------------+   |
|   |  Battery    |   |       |   |  Battery    |   |
|   +-------------+   |       |   +-------------+   |
+---------------------+       +---------------------+
        Evolution                     Evolution
        """,
        13: """
+---------------------+       +---------------------+
|   Home Assistant    |       |   Eedomus Box       |
|                     |       |                     |
|   +-------------+   |       |   +-------------+   |
|   |  Light      |   |       |   |  Light      |   |
|   +-------------+   |       |   +-------------+   |
|   |  Switch     |   |       |   |  Switch     |   |
|   +-------------+   |       |   +-------------+   |
|   |  Cover      |   |       |   +-------------+   |
|   +-------------+   |       |   |  Cover      |   |
|   |  Sensor     |   |       |   +-------------+   |
|   +-------------+   |       |   |  Sensor     |   |
|   |  Binary     |   |       |   +-------------+   |
|   +-------------+   |       |   |  Binary     |   |
|   |  Select     |   |       |   +-------------+   |
|   +-------------+   |       |   |  Select     |   |
|   |  Climate    |   |       |   +-------------+   |
|   +-------------+   |       |   |  Climate    |   |
|   |  Battery    |   |       |   +-------------+   |
|   +-------------+   |       |   |  Battery    |   |
+---------------------+       +---------------------+
        Comparison                   Comparison
        """
    }
    
    def replace_match(match, diagram_num):
        # Ajouter le schéma ASCII avant le diagramme Mermaid
        ascii_diagram = ascii_diagrams.get(diagram_num, "")
        if ascii_diagram:
            return f"```
{ascii_diagram}
```\n\n{match.group(1)}"
        return match.group(1)
    
    # Compter les diagrammes et les remplacer
    diagram_count = 0
    def replace_with_ascii(match):
        nonlocal diagram_count
        diagram_count += 1
        return replace_match(match, diagram_count)
    
    # Remplacer tous les diagrammes
    updated_content = re.sub(pattern, replace_with_ascii, content, flags=re.DOTALL)
    
    # Sauvegarder une copie de sécurité
    with open('README_backup_with_ascii.md', 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Écrire le nouveau contenu
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print(f"✅ Ajouté {diagram_count} schémas ASCII avant les diagrammes Mermaid")
    print("📁 Une copie de sécurité a été créée : README_backup_with_ascii.md")

if __name__ == "__main__":
    add_ascii_diagrams()