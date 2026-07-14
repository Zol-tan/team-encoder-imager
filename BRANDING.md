# Team Encoder Imager — rebrand kit

Fork of raspberrypi/rpi-imager (Apache-2.0 — rebranding/forking is permitted;
keep the license.txt and copyright notices in source files).

## Setup (once)

1. Fork https://github.com/raspberrypi/rpi-imager → `team-encoder-imager`
2. Clone your fork, drop these files in:
   - `rebrand.sh` → repo root
   - `os_list_teamencoder.json` → repo root
   - `gen_oslist.py` → repo root
   - `build.yml` → `.github/workflows/build.yml`
3. Edit the variables at the top of `rebrand.sh` (set OSLIST_URL to your fork's
   raw URL for os_list_teamencoder.json, or host it on zoltanstudios.au).
4. Run `./rebrand.sh`, review `git diff`, replace the icon files it lists.
5. Commit, push, then `git tag v1.0.0 && git push --tags` → CI builds
   Windows installer, Linux AppImage and macOS DMG and attaches them to a
   draft release.

## Adding a PinnerOS image (whenever you have a link)

    python3 gen_oslist.py https://your.cdn/pinneros-opi5max.img.xz \
        --name "PinnerOS (Orange Pi 5 Max)" --device opi5 \
        --merge os_list_teamencoder.json

It streams the file, computes all four size/sha256 fields, and inserts/updates
the entry. Commit + push the JSON — every installed copy of the app picks up
the new list on next launch (the list is fetched live, no app update needed).

## How the app behaves

- Device picker defaults to "Orange Pi 5 / 5 Max" showing only your images
- "Raspberry Pi (all models)" device shows the official RPi OS catalogue,
  pulled live from raspberrypi.com via subitems_url
- Telemetry is compiled out (-DENABLE_TELEMETRY=OFF) so you don't ping
  Raspberry Pi's stats server

## Notes

- Unsigned builds: Windows SmartScreen / macOS Gatekeeper will warn on first
  run. A Windows code-signing cert (or Azure Trusted Signing) fixes that later.
- First CI run is slow (Linux/macOS build Qt from source, ~1–2 h) but it's
  cached afterwards.
- Zero-code alternative: skip the fork entirely and give customers a shortcut
  to the official imager with `--repo <your os_list URL>`. Less polished, no
  branding, but zero maintenance.

## Integrating your existing Backglass installer pieces

Status of each item from settings.txt / your current tooling:

| Item | Can it go in the app? | How |
|---|---|---|
| IMAGE_URL (Mega link) | **Not as-is** | Mega encrypts files client-side; the imager's curl downloader can't fetch them. Re-host the .img.xz on a direct-HTTP host, then run gen_oslist.py on the new URL. |
| UTILITY_URL (pp-doctor.exe on Drive) | **Yes** | Run `./add_pp_doctor.sh` — bundles it into the Windows installer with a Start Menu shortcut. CI auto-downloads it via the direct link: `https://drive.usercontent.google.com/download?id=1B14Xv9vK8_Mbv8kCevnkUmGjUFbLxBx0&export=download&confirm=t` |
| DEFAULT_URL (team-encoder.com) | **Yes** | Already set as the website/branding URL throughout the kit. |
| Clear_Existing_SD_Card.ps1 | **Redundant** | rpi-imager has a built-in "Erase" option and writes at raw-disk level with admin rights, so partition-table cleaning is handled. The whole cleaner + refresh + flash dance goes away. |

### Hosting the image (replacing Mega)

Your raw image is ~22.5 GB; xz-compressed it will likely be several GB, so:

- **Cloudflare R2** (recommended): free egress (no per-download bandwidth
  charge — matters when customers worldwide pull multi-GB images), ~US$0.015/GB/mo
  storage. Put it behind downloads.team-encoder.com via a custom domain.
- **Backblaze B2 + Cloudflare**: similar economics.
- **GitHub Releases**: only if the compressed image lands under 2 GB per file — unlikely.
- Shopify hosting can't serve files this large.

Once hosted:

    python3 gen_oslist.py https://downloads.team-encoder.com/backglass-opi5.img.xz \
        --name "Team Encoder Backglass (Orange Pi 5)" --device opi5 \
        --merge os_list_teamencoder.json

Tip: compress with `xz -T0 -6 backglass.img` first — the imager decompresses
on the fly while flashing, customers download a fraction of 22.5 GB, and the
sha256 verification you get for free replaces the manual Mega download step
(which is also where your current installer's workflow breaks down).

---

## PP Doctor integration (decided approach)

PP Doctor is a **Tauri (Rust) app** — an SSH/SFTP media manager for a *running*
cabinet, not an imaging tool. It is not merged into the imager; it is bundled
alongside it and handed off to. Run in order:

    ./rebrand.sh
    ./add_pp_doctor.sh          # bundles pp-doctor.exe + Start Menu shortcut
    ./add_ppdoctor_handoff.sh   # adds "Open PP Doctor" to the Write Complete screen

The handoff button auto-hides if pp-doctor isn't present, so Linux/macOS builds
still work.

### The important part: pre-seeding the SSH connection

The backglass image entry declares `"init_format": "systemd"`. That switches on
rpi-imager's built-in customization wizard, which writes into the boot partition
**before flashing**:

| Wizard step | Writes | Why PP Doctor needs it |
|---|---|---|
| Hostname | e.g. `backglass.local` | PP Doctor's SSH target |
| User | `pi` + password | `ssh_set_credentials` |
| Wi-Fi | SSID + PSK + country | cabinet joins the network on first boot |
| Remote Access | enables SSH (+ pubkey) | every `ssh_run` / `scp_get_text` call |

Set sensible defaults for those steps and the customer flow becomes:

    flash SD  →  boot backglass  →  click "Open PP Doctor"  →  already connected

No manual SSH setup, no IP hunting. This is the integration that actually
matters, and it's configuration rather than code.

### What was deliberately NOT ported

SSH/SFTP client (russh), SQLite media DB, dirty-tracking sync, ffmpeg
transcoding, B2S generation, cache versioning/snapshots, update feed. Each
already works in PP Doctor; reimplementing them in C++/QML would take months
and produce a worse result.

### Devices / tags

`te-backglass` (Pi Zero) and `te-opi5` (cabinet) are **custom tags** defined in
this manifest, so they're independent of Raspberry Pi's official tag scheme —
works for Zero W or Zero 2 W either way. The third device passes through the
full official Raspberry Pi catalogue.

### Still open

- Re-host the backglass image off Mega (see above) — this is the last blocker.
- Confirm the backglass image is Raspberry Pi OS / systemd-based. If it isn't,
  set `"init_format": "none"` and the customization pre-seeding won't be
  available (PP Doctor would then need manual credentials on first run).

---

## Image formats: why .7z will NOT work

`PinnerOS_RELEASE.7z` (5.48 GiB, contains `Ark3588-sd-android14-opi5max.img`)
cannot be used as a hosted image, and this is not fixable by configuration.

7-Zip writes its header at the **end** of the archive, so it can only be read
from a **seekable** file. Imager streams the download straight to the SD card:

    src/downloadextractthread.cpp:379
    archive_read_open(a, this, NULL, &_archive_read, &_archive_close);
                             ^^^^ no seek callback

Verified: extracting a .7z from a seekable file returns the full image;
extracting the same archive from a pipe returns **0 bytes** and
`Error seeking in stdin`.

### Fix: repack once to .img.xz

    ./repack.sh https://www.team-encoder.com/downloads/PinnerOS_RELEASE.7z \
                "PinnerOS Cabinet (Orange Pi 5 Max)" te-opi5

Streams 7z -> xz without ever writing the ~22 GB raw .img to disk, then fills in
all four size/sha256 fields in the manifest. Upload the resulting
`PinnerOS_RELEASE.img.xz` next to the .7z and commit the manifest.

Supported hosted formats: **.xz (preferred, what every official Pi image uses),
.gz, .zip, .zst, raw .img**. Not: .7z, .rar.

Do the same for the backglass image — it needs a direct-HTTP `.img.xz` too.

## Cabinet image is Android

The Orange Pi 5 Max image is Android 14 (RK3588), so `init_format` is `none`:
Imager writes it raw and offers **no** customization wizard for it. The Pi Zero
backglass image is Linux (`init_format: systemd`), so it *does* get hostname /
user / Wi-Fi / SSH pre-seeding — which is what lets PP Doctor connect with zero
setup.


---

# .7z support (added to the app)

You cannot re-upload the image, so the app was taught to unpack `.7z` itself.
`PinnerOS_RELEASE.7z` stays exactly where it is.

## Why upstream could not do it

7-Zip stores its header at the **END** of the archive, so libarchive must be able
to SEEK. Upstream passes a NULL seek callback:

    archive_read_open(a, this, NULL, &_archive_read, &_archive_close);
                             ^^^^

Result: `Current client reader does not support seeking a device`. Proven in
isolation against libarchive: with a seek callback the same archive extracts all
419,430,400 test bytes; without one, zero.

## What changed

| File | Change |
|---|---|
| `downloadextractthread.h/.cpp` | Optional seek callback. `_supportsSeek()` defaults to **false**, so the streaming HTTP path is byte-for-byte unchanged for .xz/.gz/.zip/.zst. |
| `localfileextractthread.h/.cpp` | Reads from a `QFile`, so `_supportsSeek()` returns **true**. 7z now works for local files ("Use custom") too. |
| `localfileextractthread.cpp` (probe) | The format probe also seeks now. **This was a corruption bug**: without it a .7z failed the probe, got mistaken for a raw disk image, and the compressed bytes would have been written straight to the SD card. |
| `sevenzipdownloadextractthread.h/.cpp` | **New.** Phase 1 downloads the .7z to a temp file; phase 2 flashes from it through the existing seekable local path. Temp file is deleted afterwards. |
| `imagewriter.cpp` | Routes any URL ending in `.7z` to the new thread. |

## Cost of this approach

The customer needs **~5.5 GB free disk** for the temporary archive. The
decompressed ~22 GB image is streamed straight to the SD card and never lands on
their disk. A progress bar runs for the download, then again for the flash.

## Filling in the manifest

    python3 gen_oslist.py https://www.team-encoder.com/downloads/PinnerOS_RELEASE.7z \
        --name "PinnerOS Cabinet (Orange Pi 5 Max)" --device te-opi5 \
        --merge os_list_teamencoder.json

Downloads the archive, hashes it, then streams it through `7z x -so` to get the
inner image's size and sha256. Verified byte-exact on a real 7z.

## Verification status

- libarchive seek mechanism: **proven** (standalone C++, extracted a real 7z byte-exact)
- All four patched .cpp files: **compile clean** against Qt6 headers (`./check.sh`)
- `moc` accepts the new Q_OBJECT class: **yes**
- gen_oslist.py on a real 7z: **byte-exact** on all three hashes
- **NOT tested: an actual flash to real hardware.** This touches the disk-writing
  path. Flash a spare SD card and boot it before shipping to a customer.

See BUILDING.md.
