# Contributing to TrueFocus

Keep changes focused and explain the problem, expected behavior, and how you
verified the result. For detection changes, describe camera position and lighting
without sharing footage of other people.

## Local setup

Follow the Python setup in [README.md](README.md). Run automated checks with:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q main.py tests
```

The startup tests use mocked computer vision modules. They do not open a camera,
send notifications, or measure gaze accuracy. `test_all_directions.py` is a legacy
interactive prototype, not an automated test suite.

For a manual check, run `python main.py`, complete calibration, test looking
down and back up, then check `C`, `R`, and `Q`. Only test `T` with your own
Pushbullet account. Check video playback separately on each supported platform.

## Before opening a pull request

- Keep credentials in environment variables and redact logs.
- Keep generated builds, installers, archives, and local backups out of commits.
- Update the README when setup, controls, or behavior changes.
- Use only media you have permission to redistribute and retain attribution.
- Review `git diff --cached` and `git status --short` before pushing.
