# CI Control Plane Diagnostics

Use this runbook when the GitHub Actions `Control Plane Tests` job fails without a clear traceback in the summary view.

## What Changed

- The CI workflow now records basic Python and package-version diagnostics before running the Control Plane test suite.
- The diagnostic step runs `python --version`, `python -m pip --version`, `python -m pip freeze | sort`, and `python manage.py check` inside `control-plane/`.
- The worker lint failure `workers/agent.py: WritePrecision imported but unused` was removed so `pyflakes` can pass cleanly in CI.

## How to Read the Output

1. Confirm the Python version matches the intended GitHub Actions runner image.
2. Compare `pip freeze` output with the local environment when a failure appears only in CI.
3. Use `python manage.py check` output to catch Django configuration or import-time issues before the test command runs.
4. If the test step still fails, inspect the job log for the `Run Django tests` step and compare the failure against the diagnostic preamble.

## Suggested Reproduction Flow

1. Run the same diagnostic commands locally from `control-plane/`.
   ```bash
   python --version
   python -m pip --version
   python -m pip freeze | sort
   python manage.py check
   ```
2. Run the Django tests under the same interpreter version used by CI.
   ```bash
   python manage.py test apps/ --verbosity=2
   ```
3. If CI still fails but local checks pass, compare installed package versions and any environment-variable-dependent settings first.

## Expected Signals

- `python manage.py check` exits successfully before the test step starts.
- `python manage.py test apps/ --verbosity=2` continues to be the authoritative pass/fail signal for the Control Plane job.
- `workers/agent.py` no longer trips `pyflakes` on an unused InfluxDB import.
