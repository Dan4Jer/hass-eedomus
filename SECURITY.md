# Security Policy

## Supported versions

Only the latest release (installed via HACS) receives security fixes. Update first, then report.

| Version        | Supported |
| -------------- | --------- |
| latest (0.15+) | yes       |
| older          | no        |

## Reporting a vulnerability

**Do not open a public issue, discussion or PR for a security problem.**

- Preferred: GitHub private vulnerability reporting — the **Security** tab → **"Report a vulnerability"** (visible only to you and the maintainers).
- Or by email: **jdanoffre@gmail.com** with `[security]` in the subject.

Include: integration version, Home Assistant version, steps to reproduce, impact, and a PoC if you have one. You will get an acknowledgement within **72 hours**.

## What happens next

1. Triage and confirmation (we may ask for more details).
2. Fix developed on a private branch, reviewed, merged to `unstable`.
3. Release cut; the release notes credit the reporter (unless they prefer to stay anonymous).
4. A security advisory is published once the fix is available to everyone.

## Scope

- In scope: this repository — the integration (`custom_components/eedomus/`), the panel JS, the deploy scripts.
- Out of scope: Home Assistant core, HACS, the eedomus box and eedomus cloud themselves — report those to their respective projects.
