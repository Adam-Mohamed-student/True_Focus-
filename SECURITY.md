# Security and privacy

## Credentials

The app reads `PUSHBULLET_API_KEY` from the process environment. Notifications
are disabled when it is unset or empty. Never paste tokens into source files,
screenshots, issue reports, or build specifications. `.env.example` is only a
reference; the app does not load `.env` files automatically.

If a token has been shared or included in an old package:

1. Revoke it in [Pushbullet settings](https://www.pushbullet.com/#settings).
2. Create a replacement only if you want phone notifications.
3. Remove exposed copies and rebuild executables from cleaned source.
4. If it reached GitHub, remove it from Git history as well. Deleting the latest
   copy or adding `.gitignore` does not erase earlier commits or releases.

Old local builds and archives are not safe release artifacts. Publish newly built
packages through GitHub Releases after reviewing their contents.

## What the application processes

Camera frames and face/iris landmarks are processed locally. The current Python
app does not record or upload webcam footage. When enabled, Pushbullet receives
notification titles and messages and uses your access token to authenticate.
The separate marketing website loads external resources such as Google Fonts.

Gaze estimation is an imperfect heuristic. It is not evidence of cheating,
phone use, or intent. Use the app as a personal focus aid with the camera user's
knowledge and consent.

## Reporting a vulnerability

Do not post working credentials or sensitive footage in a public issue. Use the
repository's private vulnerability reporting feature if its owner has enabled
it, or arrange a private channel with the maintainer first. Include affected
versions, reproduction steps, impact, and redacted logs.
