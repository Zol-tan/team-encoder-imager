#!/usr/bin/env python3
"""
gen_oslist.py — turn an image URL or local file into a ready-to-paste
os_list entry for Team Encoder Imager (rpi-imager v4 JSON format).

Computes all four required fields automatically:
  image_download_size / image_download_sha256  (the compressed file)
  extract_size / extract_sha256                (the decompressed image)

Streams everything — never stores the decompressed image on disk.

Usage:
  python3 gen_oslist.py https://cdn.example.com/pinneros-opi5max.img.xz \
      --name "PinnerOS (Orange Pi 5 Max)" --device opi5
  python3 gen_oslist.py ./pinneros.img.gz --name "PinnerOS" --device opi5

Supports: .img.xz  .img.gz  .img (raw)
Paste the printed JSON object into the "os_list" array, or use
--merge os_list_teamencoder.json to insert/update it in place.
"""
import argparse, hashlib, json, lzma, zlib, sys, os, datetime, urllib.request

CHUNK = 4 * 1024 * 1024

def open_source(src):
    if src.startswith(("http://", "https://")):
        req = urllib.request.Request(src, headers={"User-Agent": "gen-oslist/1.0"})
        return urllib.request.urlopen(req)
    return open(src, "rb")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("source", help="URL or local path to .img/.img.gz/.img.xz")
    p.add_argument("--name", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--device", action="append", default=[], help="device tag, repeatable (e.g. opi5)")
    p.add_argument("--url", help="public URL if source is a local file")
    p.add_argument("--icon", default="")
    p.add_argument("--website", default="https://team-encoder.com")
    p.add_argument("--arch", default="arm64")
    p.add_argument("--merge", help="path to os_list JSON to insert/update entry in")
    a = p.parse_args()

    src = a.source
    public_url = a.url or (src if src.startswith("http") else None)
    if not public_url:
        sys.exit("Local file given: also pass --url with the public download URL.")

    # .7z needs a seekable local file (its header lives at the END of the archive),
    # so it is fetched to a temp file, hashed, then piped through `7z x -so` to get
    # the uncompressed image's size and sha256.
    if src.lower().endswith(".7z"):
        return _handle_7z(a, src, public_url)

    dl_sha, ex_sha = hashlib.sha256(), hashlib.sha256()
    dl_size = ex_size = 0

    lower = src.lower()
    if lower.endswith(".xz"):
        dec = lzma.LZMADecompressor()
        mode = "xz"
    elif lower.endswith(".gz"):
        dec = zlib.decompressobj(31)
        mode = "gz"
    else:
        dec, mode = None, "raw"

    print(f"Reading {src} ({mode}) ...", file=sys.stderr)
    with open_source(src) as f:
        while True:
            chunk = f.read(CHUNK)
            if not chunk:
                break
            dl_size += len(chunk)
            dl_sha.update(chunk)
            if dec:
                out = dec.decompress(chunk)
                ex_size += len(out)
                ex_sha.update(out)
            else:
                ex_size += len(chunk)
                ex_sha.update(chunk)
            print(f"\r  {dl_size/1e6:,.0f} MB downloaded / {ex_size/1e6:,.0f} MB extracted", end="", file=sys.stderr)
    print(file=sys.stderr)

    entry = {
        "name": a.name,
        "description": a.description or a.name,
        "url": public_url,
        "icon": a.icon,
        "website": a.website,
        "release_date": datetime.date.today().isoformat(),
        "extract_size": ex_size,
        "extract_sha256": ex_sha.hexdigest(),
        "image_download_size": dl_size,
        "image_download_sha256": dl_sha.hexdigest(),
        "devices": a.device or ["opi5"],
        "init_format": "none",
        "architecture": a.arch,
    }

    if a.merge:
        with open(a.merge) as fh:
            data = json.load(fh)
        lst = data.setdefault("os_list", [])
        for i, e in enumerate(lst):
            if e.get("name") == a.name:
                lst[i] = entry
                break
        else:
            lst.insert(0, entry)
        with open(a.merge, "w") as fh:
            json.dump(data, fh, indent=4)
        print(f"Merged into {a.merge}", file=sys.stderr)
    else:
        print(json.dumps(entry, indent=4))



def _handle_7z(a, src, public_url):
    import shutil, subprocess, tempfile, json as _json
    if shutil.which("7z") is None:
        sys.exit("Need p7zip: sudo apt install p7zip-full  (or brew install p7zip)")

    tmp = None
    if src.startswith(("http://", "https://")):
        tmp = tempfile.NamedTemporaryFile(suffix=".7z", delete=False)
        print(f"Downloading {src} ...", file=sys.stderr)
        with open_source(src) as f:
            while True:
                chunk = f.read(CHUNK)
                if not chunk:
                    break
                tmp.write(chunk)
                print(f"\r  {tmp.tell()/1e6:,.0f} MB", end="", file=sys.stderr)
        tmp.close()
        print(file=sys.stderr)
        path = tmp.name
    else:
        path = src

    # hash of the archive exactly as served
    dl_sha, dl_size = hashlib.sha256(), 0
    with open(path, "rb") as f:
        while True:
            c = f.read(CHUNK)
            if not c:
                break
            dl_sha.update(c); dl_size += len(c)

    # hash of the image INSIDE it, streamed (never lands on disk)
    print("Hashing decompressed image (streaming)...", file=sys.stderr)
    ex_sha, ex_size = hashlib.sha256(), 0
    p = subprocess.Popen(["7z", "x", "-so", path], stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL)
    while True:
        c = p.stdout.read(CHUNK)
        if not c:
            break
        ex_sha.update(c); ex_size += len(c)
        print(f"\r  {ex_size/1e6:,.0f} MB", end="", file=sys.stderr)
    p.wait()
    print(file=sys.stderr)
    if p.returncode != 0:
        sys.exit("7z extraction failed")

    entry = {
        "name": a.name,
        "description": a.description or a.name,
        "url": public_url,
        "icon": a.icon,
        "website": a.website,
        "release_date": datetime.date.today().isoformat(),
        "extract_size": ex_size,
        "extract_sha256": ex_sha.hexdigest(),
        "image_download_size": dl_size,
        "image_download_sha256": dl_sha.hexdigest(),
        "devices": a.device or ["te-opi5"],
        "init_format": "none",
        "architecture": a.arch,
    }
    if tmp:
        os.unlink(tmp.name)
    _emit(a, entry)
    return


def _emit(a, entry):
    if a.merge:
        with open(a.merge) as fh:
            data = json.load(fh)
        lst = data.setdefault("os_list", [])
        for i, e in enumerate(lst):
            if e.get("name") == a.name:
                lst[i] = entry
                break
        else:
            lst.insert(0, entry)
        with open(a.merge, "w") as fh:
            json.dump(data, fh, indent=4)
        print(f"Merged into {a.merge}", file=sys.stderr)
    else:
        print(json.dumps(entry, indent=4))


if __name__ == "__main__":
    main()