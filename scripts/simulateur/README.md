# Eedomus simulator

## Overview

This directory provides a local simulator of the eedomus API, for the
development and testing of the `hass-eedomus` Home Assistant integration
(salvaged from PR #119, story 5.1).

The repository ships with a ready-to-use demo dataset:

```text
eedomus_dump.json
thermostat_rules.json
```

These two files are the default simulation dataset.

Users can also:

- use this dataset directly with `simulator.py`;
- extract the data of their own eedomus box;
- anonymize and rename their peripherals;
- generate new files with `02_apply_renom.py`;
- use all or part of the generated files to extend or replace the
  shipped dataset.

> `02_apply_renom.py` does not merge data into the shipped files. It
> produces new `new_*` files that can serve to extend
> `eedomus_dump.json` and `thermostat_rules.json` manually, or replace
> them after review.

## Directory files

```text
simulateur/
├── 00_extract.py
├── 01_create_renom.py
├── 02_apply_renom.py
├── simulator.py
├── eedomus_dump.json
└── thermostat_rules.json
```

Additional files are created during the process:

```text
eedomus_dump_box_<address>.json
renom.csv
new_<dump>.json
new_<thermostat>.json
```

# 1. Quick start

## Prerequisites

```bash
python3 -m pip install flask requests
```

## Start with the shipped dataset

```bash
python3 simulator.py
```

Defaults:

```text
Port       : 8080
API user   : apiUser
API secret : apiPassword
```

The server listens on:

```text
http://0.0.0.0:8080
```

# 2. Simulator configuration

The port and credentials can be set on the command line:

```bash
python3 simulator.py --port 8081
python3 simulator.py --api-user testuser
python3 simulator.py --api-secret testsecret
```

or through environment variables:

```bash
export EEDOMUS_PORT=8080
export EEDOMUS_API_USER=apiUser
export EEDOMUS_API_SECRET=apiPassword

python3 simulator.py
```

# 3. Running several simulators in parallel

Several instances can run on the same machine, each on its own port:

```bash
python3 simulator.py --port 8080
python3 simulator.py --port 8081
python3 simulator.py --port 8082
```

giving three independent APIs:

```text
http://<host>:8080
http://<host>:8081
http://<host>:8082
```

Ports can also be set with the `EEDOMUS_PORT` environment variable:

```bash
EEDOMUS_PORT=8080 python3 simulator.py
EEDOMUS_PORT=8081 python3 simulator.py
```

This notably allows simulating several eedomus boxes and testing
several `hass-eedomus` configurations in parallel.

### Per-instance dataset

Each instance loads the `eedomus_dump.json` and
`thermostat_rules.json` files sitting next to the script. To run
several simulators with **different datasets**, use one directory per
instance, each with its own `simulator.py`, `eedomus_dump.json` and
optionally `thermostat_rules.json`:

```text
simulateur_box_1/
├── simulator.py
├── eedomus_dump.json
└── thermostat_rules.json

simulateur_box_2/
├── simulator.py
├── eedomus_dump.json
└── thermostat_rules.json
```

Then:

```bash
cd simulateur_box_1
python3 simulator.py --port 8080

cd ../simulateur_box_2
python3 simulator.py --port 8081
```

# 4. Loaded data

`simulator.py` loads `eedomus_dump.json`:

```json
{
  "periph_list": [],
  "value_list": [],
  "caract": []
}
```

`thermostat_rules.json` is loaded when present.

# 5. Simulated API

The server exposes:

```text
GET  /api/get
GET  /api/set
POST /simulate/change
```

Supported actions:

```text
auth.test
periph.list
periph.value_list
periph.caract
periph.value
periph.history
```

`periph.history` serves a synthetic, deterministic history generated
from the dump (story 5.2, spec-eedomus-simulator CAP-2): hourly points
over `EEDOMUS_HISTORY_YEARS` years (default 3) ending at the
peripheral's `last_value_change`, at most `EEDOMUS_HISTORY_DENSITY`
points per hour (default 1). The response honors the production
client's chunking contract — points strictly after the epoch `start`
parameter and up to epoch `end`, ascending, capped at 10 000 points
per call; a chunk shorter than the cap means the series is complete.
Peripherals whose `last_value` is not numeric get an empty history.
The generation is a pure function of the dump (no wall clock): the
same dump always yields the same series.

Example:

```bash
curl "http://127.0.0.1:8080/api/get?action=auth.test&api_user=apiUser&api_secret=apiPassword"
```

To change a peripheral:

```bash
curl "http://127.0.0.1:8080/api/set?action=periph.value&periph_id=thermostat&value=20&api_user=apiUser&api_secret=apiPassword"
```

Changes stay in memory only.

# 6. Simulating an external change

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"periph_id":"thermostat_temp","value":"18.5"}' \
  http://127.0.0.1:8080/simulate/change
```

This route currently does not require the eedomus API authentication.

# 7. Thermostat simulation

A rule contains:

```text
setpoint_id
sensor_id
switch_id
on_value
off_value
```

Principle:

```text
if setpoint > measured temperature
    command = on_value
else
    command = off_value
```

There is currently no hysteresis and no delay.

# 8. Building a dataset from a real box

The recommended flow:

```text
eedomus box
    |
    v
00_extract.py
    |
    v
eedomus_dump_box_<address>.json
    |
    v
01_create_renom.py
    |
    v
renom.csv
    |
    v
edit / anonymize
    |
    v
02_apply_renom.py
    |
    +--> new_<dump>.json
    |
    +--> new_<thermostat>.json
```

# 9. `00_extract.py`

Parameters on the command line:

```bash
python3 00_extract.py \
  --ip 192.168.1.10 \
  --api-user my_user \
  --api-secret my_secret
```

or through environment variables:

```bash
export EEDOMUS_HOST=192.168.1.10
export EEDOMUS_API_USER=my_user
export EEDOMUS_API_SECRET=my_secret
```

The script fetches `periph.list`, `periph.value_list`, `periph.caract`
and produces `eedomus_dump_box_<address>.json`.

# 10. `01_create_renom.py`

Example:

```bash
python3 01_create_renom.py \
  --json eedomus_dump_box_192_168_1_10.json \
  --csv renom.csv
```

The CSV contains:

```text
periph_id
name
parent_periph_id
usage_id
new_periph_id
new_name
```

To delete a peripheral: `new_periph_id = non` (no) and an empty
`new_name`.

# 11. `02_apply_renom.py`

Example:

```bash
python3 02_apply_renom.py \
  --dump-file eedomus_dump_box_192_168_1_10.json \
  --csv renom.csv \
  --thermostat thermostat_rules.json
```

Output files carry the `new_` prefix by default:

```text
eedomus_dump_box_192_168_1_10.json
    -> new_eedomus_dump_box_192_168_1_10.json

thermostat_rules.json
    -> new_thermostat_rules.json
```

Output names can also be forced with `--news-dump-file` and
`--new-thermostat`.

The script validates IDs, duplicates, CSV coverage of all
peripherals, parent/child relations, deletions, new-ID uniqueness and
the thermostat references.

# 12. Extending the shipped files after `02_apply_renom.py`

The `new_*` files can extend the reference dataset. Full replacement
after review:

```bash
cp new_eedomus_dump_box_192_168_1_10.json eedomus_dump.json
cp new_thermostat_rules.json thermostat_rules.json
```

To extend the existing dataset instead, pick the useful peripherals
from `new_<dump>.json` and add them to the matching sections of
`eedomus_dump.json` (`periph_list`, `value_list`, `caract` must stay
consistent), and the useful rules of `new_thermostat_rules.json` into
`thermostat_rules.json`.

### Important

`02_apply_renom.py` does not merge automatically. After a manual
addition, check the `periph_id` uniqueness, the `parent_periph_id`
consistency, the presence of the peripherals in every needed section,
and the `setpoint_id` / `sensor_id` / `switch_id` references.

# 13. Security and anonymization

Data coming from `periph.caract?show_config=1` may contain sensitive
information that the renaming does not remove automatically. Before
publishing, check in particular: GPS coordinates, URLs, OAuth tokens,
`VAR1`/`VAR2`/`VAR3`, external identifiers, phone numbers, network
addresses, person names, room names revealing personal information.
The `renom.csv` renaming mainly covers `periph_id`, `name` and
`parent_periph_id` - it is not a complete anonymization by itself.

# 14. Persistence

Changes made through `/api/set` and `/simulate/change` stay in memory
and never modify `eedomus_dump.json`. Restarting the simulator
restores the file's initial values.

# 15. Recommended workflow to add peripherals to the shipped dataset

```bash
# 1. Extract
python3 00_extract.py \
  --ip 192.168.1.10 \
  --api-user my_user \
  --api-secret my_secret

# 2. Create the CSV
python3 01_create_renom.py \
  --json eedomus_dump_box_192_168_1_10.json \
  --csv renom.csv

# 3. Edit renom.csv

# 4. Generate the remapped files
python3 02_apply_renom.py \
  --dump-file eedomus_dump_box_192_168_1_10.json \
  --csv renom.csv \
  --thermostat thermostat_rules.json

# 5. Review the remaining sensitive information

# 6. Extend eedomus_dump.json
# 7. Extend thermostat_rules.json when needed

# 8. Test
python3 simulator.py
```

# 16. Limits

The simulator does not emulate a whole eedomus box - it reproduces
only the functions the current `hass-eedomus` tests need. The
reference files shipped with the simulator are `eedomus_dump.json` and
`thermostat_rules.json`; the `new_*` files produced by
`02_apply_renom.py` serve to prepare, validate and extend that
reference dataset.
