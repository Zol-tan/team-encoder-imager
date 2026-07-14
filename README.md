# Team Encoder Imager

Bootable-media writer for Team Encoder pinball cabinets — flashes the
PinnerPi backglass image (Raspberry Pi Zero) and the cabinet image
(Orange Pi 5 / 5 Max), and can also write any official Raspberry Pi OS.

Bundles **PP Doctor** and launches it straight from the Write Complete screen.

Derived from [Raspberry Pi Imager](https://github.com/raspberrypi/rpi-imager)
(Apache-2.0). See `NOTICE`.

## Before the first build

1. **Icons** — replace `src/icons/rpi-imager.ico` (Windows) and
   `src/icons/AppIcon-compiled.icns` (macOS). Drop manifest icons in `assets/`.
2. **Host the backglass image** on direct HTTP (Mega will not work — see
   BRANDING.md), then:
   ```
   python3 gen_oslist.py https://your.host/pinnerpi-backglass.img.xz \
       --name "PinnerPi Backglass" --device te-backglass \
       --merge os_list_teamencoder.json
   ```
3. **Host `os_list_teamencoder.json`** and set that URL as `OSLIST_URL` in
   `src/config.h` (currently a placeholder).

## Build

Push a tag; GitHub Actions builds all three platforms into a draft release:

```
git tag v1.0.0 && git push --tags
```

First run compiles Qt from source on Linux/macOS (~1–2 h, cached afterwards).
Builds are unsigned — Windows SmartScreen and macOS Gatekeeper will warn users.

Local builds: see CONTRIBUTING.md (upstream instructions still apply), adding
`-DENABLE_TELEMETRY=OFF`.
