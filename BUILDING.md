# How to build

Three ways, easiest first. **You almost certainly want option 1.**

---

## 1. GitHub Actions — no local setup at all (recommended)

The repo already contains `.github/workflows/build.yml`. Push the code, push a
tag, and GitHub builds all three platforms for you on their machines.

```bash
cd team-encoder-imager
git init && git add -A && git commit -m "Team Encoder Imager"
git remote add origin git@github.com:YOURUSER/team-encoder-imager.git
git push -u origin main

git tag v1.0.0
git push --tags
```

Then watch the **Actions** tab. When it finishes you get a **draft Release**
with:

| Artifact | Job | Roughly how long |
|---|---|---|
| Windows installer (.exe) | `windows` | **10–20 min** — uses prebuilt Qt |
| Linux AppImage | `linux-appimage` | 1–2 h first run, ~15 min after (Qt is cached) |
| macOS DMG | `macos` | 1–2 h first run, ~15 min after (Qt is cached) |

The Windows job is the fast one, and it's the one your customers actually use.
If you only care about Windows, you can delete the `linux-appimage` and `macos`
jobs from `build.yml` and every build finishes in under 20 minutes.

You can also trigger a build without tagging: **Actions → build → Run workflow**.

---

## 2. Check the code compiles — 30 seconds, no Qt build

A full build compiles Qt from source, which is a painful loop for finding a
typo. To just check the C++ is valid:

```bash
sudo apt install qt6-base-dev qt6-declarative-dev libcurl4-openssl-dev \
                 libarchive-dev g++
./check.sh
```

```
  PASS  src/imagewriter.cpp
  PASS  src/downloadextractthread.cpp
  PASS  src/localfileextractthread.cpp
  PASS  src/sevenzipdownloadextractthread.cpp
  PASS  moc src/sevenzipdownloadextractthread.h
  PASS  moc src/imagewriter.h
All good.
```

This does **not** produce a binary. It only proves the code compiles — use it
before pushing so you don't wait 20 minutes to discover a missing semicolon.

---

## 3. Build locally

### Windows (what your customers run)

1. Install the **Qt online installer** → choose **Qt 6.9** with the
   **MinGW 64-bit** toolchain.
2. Install **Inno Setup**: https://jrsoftware.org/isdl.php
3. Install **VS Code** + the Qt Extension Pack.
4. Open the repo in VS Code. In the CMake plugin settings, set Configure Args:
   ```
   -DQt6_ROOT=C:\Qt\6.9.0\mingw_64
   -DMINGW64_ROOT=C:\Qt\Tools\mingw1310_64
   -DENABLE_INNO_INSTALLER=ON
   -DIMAGER_SIGNED_APP=OFF
   -DENABLE_TELEMETRY=OFF
   ```
5. Select the **MinSizeRel** variant, then build the **`inno_installer`** target.
6. Installer lands in `build\installer\`.

Drop `pp-doctor.exe` into `src\windows\extras\` first if you want it bundled
locally (CI downloads it automatically).

### Linux

```bash
sudo apt install --no-install-recommends build-essential cmake git libgnutls28-dev
sudo ./qt/build-qt.sh        # builds Qt 6.9 into /opt/Qt — takes 1–2 hours, once
./create-appimage.sh
./Team_Encoder_Imager-*.AppImage
```

### macOS

```bash
./qt/build-qt-macos.sh       # 1–2 hours, once
cmake -S src -B build -DCMAKE_BUILD_TYPE=MinSizeRel \
      -DQt6_ROOT=/opt/Qt/6.9.1/macos \
      -DIMAGER_SIGNED_APP=OFF -DENABLE_TELEMETRY=OFF
cmake --build build -j
```

DMG appears in `build/`.

---

## Signing

Builds are **unsigned**. Windows SmartScreen will warn on first run, and macOS
Gatekeeper will require right-click → Open. To fix:

- **Windows**: get a code-signing certificate (or Azure Trusted Signing), then
  build with `-DIMAGER_SIGNED_APP=ON`.
- **macOS**: needs an Apple Developer subscription + a "Developer ID"
  certificate, then `-DIMAGER_SIGNED_APP=ON -DIMAGER_NOTARIZE_APP=ON`.

Worth doing before you ship to paying customers — an unsigned installer that
asks for admin rights to write to a disk looks exactly like malware.

---

## Before you ship: test the flash

The 7z support touches the disk-writing path. Flash a **spare SD card** and boot
it before this goes anywhere near a customer.
