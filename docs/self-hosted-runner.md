# Self-hosted runner for the E2E suite (story 101)

The E2E suite (`tests/e2e/`) needs the live Home Assistant instance on
the Raspberry Pi (192.168.1.5) and a long-lived `HA_TOKEN`; it cannot
run on GitHub-hosted runners.

## Finding: the Pi itself cannot host the runner

The Pi runs Home Assistant OS - an **Alpine-based appliance**. The
official GitHub Actions runner is a glibc x64/arm64 binary: it does not
run on musl-based Alpine, and HAOS offers no package manager or shell
add-on surface for it. A runner on the Pi would mean building and
maintaining a custom HA add-on - out of scope.

## The practical host: a LAN machine

The runner can live on any machine with LAN access to the Pi - the
development Mac is the natural host (it already reaches
`http://192.168.1.5:8123`).

### Installation (once, on the LAN host)

1. On GitHub: Settings > Actions > Runners > New self-hosted runner -
   copy the registration token.
2. On the host:

   ```bash
   mkdir actions-runner && cd actions-runner
   # download per GitHub's instructions (macOS arm64), then:
   ./config.sh --url https://github.com/Dan4Jer/hass-eedomus \
     --token <REGISTRATION_TOKEN> --labels e2e --ephemeral
   ./run.sh
   ```

   For a permanent service: `brew install github/actions-runner` is not
   official - use `./svc.sh install` (Linux) or a launchd agent
   (macOS) wrapping `./run.sh`.

3. Repository secrets/variables (Settings > Secrets and variables >
   Actions):
   - secret `E2E_HA_TOKEN` = the long-lived access token
   - variable `E2E_HA_URL` = `http://192.168.1.5:8123`
   - variable `E2E_RUNNER` = `enabled` (wakes the dormant `e2e` job)

### What runs

The `e2e` job in `.github/workflows/tests.yml` (dormant until
`E2E_RUNNER=enabled`): checkout, Python 3.11, then
`pytest tests/e2e/ -q` against the live instance. The runner never
deploys anything (AD-10: git-only deploys stay the rule).

## The user's gesture (hitl)

The registration token and the validation that the runner is connected
(Settings > Actions > Runners shows it idle) are the user's to
provide; everything else is scripted above.
