## 🗺️ Architecture Visuelle des Entités

### 🎯 Tableau de Correspondance Eedomus → Home Assistant

```mermaid
flowchart TD
    subgraph Legend[Legend]
        A[HA Entity] -->|maps to| B[ha_entity]
        C[Eedomus Type] -->|usage_id| D[usage_id]
    end

    subgraph MappingTable[Eedomus to HA Mapping]
        %% Lights
        EedomusLight[Eedomus Light] --> HALight[HA Light]
        EedomusLight --> Light1[usage_id=1]
        EedomusLight --> LightRGBW[PRODUCT_TYPE_ID=2304]
        
        %% Select Entities
        EedomusSelect[Eedomus Select] --> HASelect[HA Select]
        EedomusSelect --> SelectGroup[usage_id=14]
        EedomusSelect --> SelectColor[usage_id=82]
        
        %% Climate
        EedomusClimate[Eedomus Climate] --> HAClimate[HA Climate]
        EedomusClimate --> ClimateSetpoint[usage_id=15]
        
        %% Sensors
        EedomusSensor[Eedomus Sensor] --> HASensor[HA Sensor]
        EedomusSensor --> SensorTemp[usage_id=7]
        EedomusSensor --> SensorEnergy[usage_id=26]
        
        %% Binary Sensors
        EedomusBinary[Eedomus Binary] --> HABinary[HA Binary Sensor]
        EedomusBinary --> BinaryMotion[usage_id=37]
        
        %% Switches
        EedomusSwitch[Eedomus Switch] --> HASwitch[HA Switch]
        EedomusSwitch --> SwitchConsumption[usage_id=2]
    end

    %% Parent-Child Relationships
    subgraph Relationships[Parent-Child Relationships]
        RGBWParent[RGBW Light 1077644] --> RGBWChild1[Red 1077645]
        RGBWParent --> RGBWChild2[Green 1077646]
        RGBWParent --> RGBWColorPreset[Color Preset 1077650]
        
        Thermostat[Setpoint 1252441] --> TempSensor[Temperature 1235856]
        
        MotionSensor[Motion 1090995] --> MotionBattery[Battery 1090995-Battery]
    end

    %% Legend
    classDef new fill:#9f9,stroke:#333
    classDef fixed fill:#ff9,stroke:#333
    classDef auto fill:#99f,stroke:#333

    SelectColor:::new
    SensorEnergy:::new
    BinaryMotion:::fixed
    SwitchConsumption:::auto
    RGBWColorPreset:::new
    MotionBattery:::new

    style Legend fill:#f9f,stroke:#333
    style MappingTable fill:#fff,stroke:#333
    style Relationships fill:#fff,stroke:#333
```

### Diagramme Global de Mapping des Entités

```mermaid
flowchart TD
    subgraph Eedomus[Eedomus Box]
        A[Eedomus Devices] -->|API| B[Z-Wave Classes]
        A -->|API| C[Usage IDs]
        A -->|API| D[PRODUCT_TYPE_ID]
        A -->|API| E[Values & States]
    end
    
    subgraph HA[Home Assistant]
        B --> F[Mapping System]
        C --> F
        D --> F
        E --> F
        
        F -->|ha_entity| G[Light Entities]
        F -->|ha_entity| H[Switch Entities]
        F -->|ha_entity| I[Cover Entities]
        F -->|ha_entity| J[Sensor Entities]
        F -->|ha_entity| K[Binary Sensor Entities]
        F -->|ha_entity| L[Select Entities]
        F -->|ha_entity| M[Climate Entities]
        F -->|ha_entity| N[Battery Sensors]
    end
    
    style Eedomus fill:#f9f,stroke:#333
    style HA fill:#bbf,stroke:#333
    style F fill:#9f9,stroke:#333
```

### Exemple Concret : Device RGBW avec Couleurs Prédéfinies

```mermaid
flowchart LR
    subgraph RGBWDevice[RGBW Light Device - Led Meuble Salle de bain]
        direction TB
        Parent[Parent: 1077644
usage_id=1
hentity=light
subtype=rgbw] -->|contains| R[Red: 1077645
usage_id=1] 
        Parent -->|contains| G[Green: 1077646
usage_id=1] 
        Parent -->|contains| B[Blue: 1077647
usage_id=1] 
        Parent -->|contains| W[White: 1077648
usage_id=1] 
        Parent -->|contains| C[Consumption: 1077649
usage_id=26
hentity=sensor
subtype=energy] 
        Parent -->|contains| P[Color Preset: 1077650
usage_id=82
hentity=select
subtype=color_preset] 
    end
    
    style Parent fill:#9f9,stroke:#333
    style R fill:#f99,stroke:#333
    style G fill:#9f9,stroke:#333
    style B fill:#99f,stroke:#333
    style W fill:#fff,stroke:#333
    style C fill:#ff9,stroke:#333
    style P fill:#f9f,stroke:#333
```

### Exemple Concret : Thermostat avec Capteur Associé

```mermaid
flowchart TD
    subgraph ThermostatSystem[Thermostat System - Consigne Salon]
        direction TB
        Setpoint[Setpoint: 1252441
usage_id=15
hentity=climate
subtype=temperature_setpoint] 
        Setpoint -->|associated with| Sensor[Temperature: 1235856
usage_id=7
hentity=sensor
subtype=temperature] 
        Setpoint -->|controls| Heating[Heating: 1235855
usage_id=38
hentity=climate
subtype=fil_pilote] 
    end
    
    style Setpoint fill:#9f9,stroke:#333
    style Sensor fill:#99f,stroke:#333
    style Heating fill:#f99,stroke:#333
```

### Flux de Données Complet

```mermaid
flowchart LR
    subgraph Eedomus[Eedomus Box]
        API[API Endpoint] -->|JSON| Devices[Devices Database]
        Devices -->|Update| States[Current States]
        States -->|Webhook| HA
    end
    
    subgraph HA[Home Assistant]
        Webhook[Webhook Receiver] --> Coordinator[Data Coordinator]
        Coordinator -->|Refresh| API
        Coordinator -->|Update| Entities[HA Entities]
        
        Entities -->|Light| LightPlatform
        Entities -->|Switch| SwitchPlatform
        Entities -->|Climate| ClimatePlatform
        Entities -->|Sensor| SensorPlatform
        Entities -->|Binary Sensor| BinarySensorPlatform
        Entities -->|Select| SelectPlatform
        Entities -->|Cover| CoverPlatform
        Entities -->|Battery| BatterySensors
    end
    
    style Eedomus fill:#f96,stroke:#333
    style HA fill:#9f9,stroke:#333
    style Coordinator fill:#bbf,stroke:#333
```

### Légende des Couleurs

```mermaid
graph LR
    A[Green - Main Entities] -->|Example| B[Light, Climate, Coordinator]
    C[Red - Actions] -->|Example| D[Set Value, Webhook, API]
    E[Yellow - Data] -->|Example| F[States, Values, Battery]
    G[Blue - Platforms] -->|Example| H[Sensor, Binary Sensor, Select]
    I[Purple - Systems] -->|Example| J[Eedomus, Home Assistant]
```

### Diagramme d'Intégration Git

```mermaid
gitGraph
    commit "Main Branch"
    branch feature/scene-to-select-refactor
    checkout feature/scene-to-select-refactor
    commit "Add select entities"
    commit "Fix values field"
    checkout main
    branch feature/improved-entity-mapping
    checkout feature/improved-entity-mapping
    commit "Improve climate entities"
    commit "Add battery sensors"
    merge feature/scene-to-select-refactor
    commit "Final integration"
```

## 📋 Fonctionnalités Supportées par Version

| Version | Plateformes | Entités Spéciales | Changements Majeurs |
|---------|-------------|-------------------|---------------------|
| 0.12.0 | 7 | Battery sensors, Color presets as select | Améliorations majeures des entités |
| 0.11.0 | 7 | Select entities | Migration Scene→Select |
| 0.10.0 | 7 | Climate entities | Support des thermostats |
| 0.9.0 | 6 | Mapping system | Refonte du mapping |
| 0.8.0 | 6 | Scene entities | Support des scènes |
