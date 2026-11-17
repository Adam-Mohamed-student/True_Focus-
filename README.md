# TrueFocus

### Look up. Get back to what matters.

A webcam-powered focus reminder that interrupts prolonged downward glances with
a video of your choice. Built with Python, OpenCV, and MediaPipe, with optional
Pushbullet notifications for your phone.

**Local camera processing · Personal calibration · Custom video reminders**

> TrueFocus estimates gaze; it cannot tell whether you are using a phone or
> actually doomscrolling. It is a personal productivity prototype, not a validated
> exam-proctoring or cheating-detection system.

## How it works

1. **Calibrate:** look straight at your screen, then down, following the prompts.
2. **Focus:** the webcam tracks one face and estimates eye position, with smoothing
   and head-pose checks to reduce noisy detections.
3. **Get a reminder:** looking down for two seconds starts a local MP4 video.
4. **Look back up:** the app attempts to stop playback when your gaze returns.

The preview shows detection feedback and timer progress. Losing face tracking
resets the timer and stops an active reminder.

## Quick start

Use **64-bit Python 3.11 or 3.12**, a webcam, and a desktop video player.
The pinned MediaPipe version uses its older `solutions` API; Python 3.13+ is
outside this project's supported dependency setup.

Windows is the primary packaging target. macOS has a QuickTime/AppleScript
playback path, which needs separate manual testing. Linux playback is not
implemented.

Download the source from your GitHub repository and open a terminal in its root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

If PowerShell blocks activation, use `.\.venv\Scripts\python.exe` in place of
`python`; activation is optional. On macOS, create the environment with
`python3.12 -m venv .venv` and activate it with `source .venv/bin/activate`.

Run from the project root so the app can find `assets/`. Allow camera access for
your terminal or Python process. Put an MP4 you have permission to use in
`assets/`; keep just one there to make video selection predictable. In a packaged
installation, put `assets/` beside `DoomscrollBlocker.exe`.

On Windows, [VLC](https://www.videolan.org/vlc/) in its default installation
location provides the most predictable playback. The app falls back to Windows
Media Player, then your default MP4 application.

## Controls

With the camera preview focused:

| Key | Action |
| --- | --- |
| `Q` or `Esc` | Quit and release the webcam |
| `C` | Recalibrate gaze detection |
| `R` | Reset the detection timer |
| `T` | Request a test phone notification, if enabled |

Notifications share a ten-second cooldown, so repeated tests may be suppressed.

## Optional phone notifications

The app works without an account or API key. To enable notifications, create
your own access token in [Pushbullet settings](https://www.pushbullet.com/#settings),
sign into Pushbullet on your phone, and set the environment variable before
starting the app:

```powershell
$env:PUSHBULLET_API_KEY = Read-Host "Pushbullet access token" -MaskInput
python main.py
```

`-MaskInput` requires PowerShell 7.1+. In Windows PowerShell 5.1, configure a user
environment variable through Windows settings and reopen your terminal. A
packaged executable also reads the environment it inherits when launched.

[.env.example](.env.example) documents the variable. **The app does not load
`.env` files automatically.** Never put a token in Python source or a build file.

Camera frames stay on your computer; enabling Pushbullet sends notification
titles and messages to its service. See [SECURITY.md](SECURITY.md).

## Tune your reminder

These settings live near the top of [main.py](main.py):

| Setting | Default | Purpose |
| --- | --- | --- |
| `TIMER_DURATION` | `2.0` seconds | Grace period before playing a reminder |
| `USE_CALIBRATION` | `True` | Learn your straight-ahead and downward gaze |
| `SMOOTHING_FRAMES` | `7` | Average recent measurements; more frames add delay |
| `HEAD_POSE_CHECK` | `True` | Require stronger evidence when your head is turned |
| `MIN_CONFIDENCE` | `0.2` | Ignore measurements below this confidence |
| `CALIBRATION_SAMPLES` | `50` | Frames collected for each calibration pose |
| `LOOKING_DOWN_THRESHOLD` | `0.25` | Fallback threshold when calibration is disabled or fails |
| `DEBOUNCE_THRESHOLD` | `0.45` | Gaze threshold used while a video is playing |

Good lighting and a camera near screen height help. Recalibrate after changing
your posture or camera position. Looking down to read or write can trigger a
reminder too.

## Project layout

```text
main.py            Maintained webcam application
assets/            Local reminder videos
WEBSITE/           Separate static marketing website
tests/             Automated startup and credential configuration checks
requirements.txt   Runtime dependencies
doomscroll.spec    Windows PyInstaller build specification
build_exe.bat      Windows executable build helper
installer.iss      Optional Inno Setup installer definition
```

The website contains product concepts and performance claims that are not
validated by this Python prototype. Its exam-mode and accuracy descriptions
should not be treated as implemented or independently measured features.
Local backup scripts and `test_all_directions.py` are historical prototypes and
are excluded from Git; the latter is an interactive app, not an automated test.

## Build for Windows

From the activated environment:

```powershell
python -m pip install pyinstaller
.\build_exe.bat
```

The helper builds from `doomscroll.spec`, preserving the MediaPipe model resources,
and offers to launch `dist/DoomscrollBlocker.exe`. Test calibration and playback
before distributing it. The current windowed build hides terminal calibration
instructions; use the source version when you need those prompts.

To create an installer, install [Inno Setup](https://jrsoftware.org/isinfo.php),
obtain Microsoft's official x64 Visual C++ Redistributable, place it at the
project root as `vc_redist.x64.exe`, and compile `installer.iss`. The installer
definition copies `assets/` beside the executable. Generated packages and the
redistributable are excluded from Git.

Publish reviewed, freshly built binaries as **GitHub Releases**, rather than
committing them to the source repository. Old packages can retain embedded tokens.

## Checks and limitations

```powershell
python -m pip check
python -m unittest discover -s tests -v
python -m compileall -q main.py tests
```

Startup tests run without a webcam or network calls. GitHub Actions checks the
dependencies and startup behavior on Windows with Python 3.11 and 3.12. These
checks do not validate gaze accuracy, installer behavior, or media playback.

- The app reminds you; it does not block websites, lock your phone, or enforce focus.
- Glasses, lighting, posture, and camera placement can affect detection.
- The displayed accuracy statistics are internal event counts, not a benchmark.
- Windows cleanup can close other VLC or Windows Media Player sessions; macOS
  playback can close existing QuickTime documents. Save unrelated media work first.
- The Windows default-player fallback may not stop automatically.

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and manual checks.

## Credits and licensing

The previous README credits
[Doomscrolling: Skyrim Edition by reinesana](https://github.com/reinesana/doomscrolling-skyrim-edition).
Preserve upstream copyright and license notices when distributing derived code.
The old README mentioned MIT, but no top-level license file was supplied; confirm
the upstream license and add an appropriate `LICENSE` before presenting this as
licensed open-source software. Videos and artwork may have separate rights;
only redistribute assets you have permission to share.
