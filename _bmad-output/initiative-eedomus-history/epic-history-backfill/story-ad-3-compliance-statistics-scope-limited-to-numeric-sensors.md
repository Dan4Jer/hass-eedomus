---
id: 7
type: story
title: "AD-3 compliance: statistics scope limited to numeric sensors"
parent: epic-history-backfill
covers: [CAP-1, CAP-5]
after: [2]
risk: medium
---

# AD-3 compliance: statistics scope limited to numeric sensors

## Description

La file de backfill dérive désormais d'un ensemble _backfill_eligible_peripherals (periphs mappés entité sensor avec valeur numérique résoluble — float/int déclaré, ou value_list avec au moins une valeur numérique, AD-6) et non plus de _dynamic_peripherals : les états discrets (light/switch/cover/climate/...) sortent de la file, les capteurs numériques statiques (températures, humidité) y entrent. Prioritize et retry_now refusent un periph non éligible (une entrée morte ne traîne pas en tête de file).

## Acceptance Criteria

Verify: Un capteur de température statique (ex. Température Sonoff Salon, periph 3516814) apparaît dans la file eedomus/get_backfill_state et son backfill importe ses statistics antérieures à l'installation HA ; aucune entité discrète ne figure dans la file.

## References

- parent — _bmad-output/initiative-eedomus-history/epic-history-backfill/epic-history-backfill.md
- ../../planning-artifacts/architecture/architecture-hass-eedomus-2026-09-27/ARCHITECTURE-SPINE.md#ad-3
