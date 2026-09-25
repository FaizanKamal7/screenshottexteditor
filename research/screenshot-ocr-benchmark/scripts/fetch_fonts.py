"""Download the pinned OFL font files used by the templates and write fonts/fonts.lock.json.

Stdlib only, so it runs on any Python 3.10+. Every file is recorded with its
source URL and SHA-256. Re-running verifies existing files against the lock
instead of silently replacing them.

    python scripts/fetch_fonts.py            # download + write lock
    python scripts/fetch_fonts.py --verify   # verify files against lock only
"""

import argparse
import hashlib
import io
import json
import os
import sys
import tarfile
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(ROOT, "fonts")
LOCK_PATH = os.path.join(FONTS_DIR, "fonts.lock.json")

FONTSOURCE_VERSION = "5.3.0"
FONTSOURCE = "https://cdn.jsdelivr.net/npm/@fontsource/{pkg}@" + FONTSOURCE_VERSION + "/{path}"

# (family, weight, package, file stem) — fontsource "latin" subsets.
FONTSOURCE_FILES = [
    ("Inter", 400, "inter"), ("Inter", 500, "inter"), ("Inter", 600, "inter"), ("Inter", 700, "inter"),
    ("Roboto", 400, "roboto"), ("Roboto", 500, "roboto"), ("Roboto", 700, "roboto"),
    ("Noto Sans", 400, "noto-sans"), ("Noto Sans", 600, "noto-sans"),
    ("Source Serif 4", 400, "source-serif-4"), ("Source Serif 4", 600, "source-serif-4"),
    ("JetBrains Mono", 400, "jetbrains-mono"), ("JetBrains Mono", 700, "jetbrains-mono"),
]

LIBERATION_URL = (
    "https://github.com/liberationfonts/liberation-fonts/files/7261482/liberation-fonts-ttf-2.1.5.tar.gz"
)
LIBERATION_MEMBERS = {
    "LiberationSans-Regular.ttf": ("Liberation Sans", 400),
    "LiberationSans-Bold.ttf": ("Liberation Sans", 700),
    "LICENSE": None,
}

SELAWIK_URL = "https://github.com/microsoft/Selawik/releases/download/1.01/Selawik_Release.zip"
SELAWIK_MEMBERS = {
    "selawk.ttf": ("Selawik", 400),
    "selawksb.ttf": ("Selawik", 600),
    "selawkb.ttf": ("Selawik", 700),
}
SELAWIK_LICENSE_URL = (
    "https://raw.githubusercontent.com/microsoft/Selawik/89362e84731d1f5777fa078fd4d5ebbd339e4378/LICENSE.txt"
)


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "screenshot-ocr-benchmark/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(rel: str, data: bytes) -> None:
    path = os.path.join(FONTS_DIR, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def fetch() -> dict:
    entries = []
    licenses = []

    for family, weight, pkg in FONTSOURCE_FILES:
        rel_src = f"files/{pkg}-latin-{weight}-normal.woff2"
        url = FONTSOURCE.format(pkg=pkg, path=rel_src)
        data = _get(url)
        rel = f"{pkg}/{pkg}-latin-{weight}-normal.woff2"
        _write(rel, data)
        entries.append({"family": family, "weight": weight, "file": rel, "url": url, "sha256": _sha256(data)})
    for pkg in sorted({p for _, _, p in FONTSOURCE_FILES}):
        url = FONTSOURCE.format(pkg=pkg, path="LICENSE")
        data = _get(url)
        _write(f"{pkg}/LICENSE", data)
        licenses.append({"file": f"{pkg}/LICENSE", "url": url, "sha256": _sha256(data)})

    tar_bytes = _get(LIBERATION_URL)
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tar:
        for member in tar.getmembers():
            name = os.path.basename(member.name)
            if name not in LIBERATION_MEMBERS:
                continue
            data = tar.extractfile(member).read()
            rel = f"liberation-sans/{name}"
            _write(rel, data)
            meta = LIBERATION_MEMBERS[name]
            if meta is None:
                licenses.append({"file": rel, "url": LIBERATION_URL, "sha256": _sha256(data)})
            else:
                entries.append(
                    {"family": meta[0], "weight": meta[1], "file": rel, "url": LIBERATION_URL + "#" + member.name,
                     "sha256": _sha256(data)}
                )

    zip_bytes = _get(SELAWIK_URL)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for info in zf.infolist():
            name = os.path.basename(info.filename)
            if name not in SELAWIK_MEMBERS:
                continue
            data = zf.read(info)
            rel = f"selawik/{name}"
            _write(rel, data)
            family, weight = SELAWIK_MEMBERS[name]
            entries.append(
                {"family": family, "weight": weight, "file": rel, "url": SELAWIK_URL + "#" + info.filename,
                 "sha256": _sha256(data)}
            )
    data = _get(SELAWIK_LICENSE_URL)
    _write("selawik/LICENSE.txt", data)
    licenses.append({"file": "selawik/LICENSE.txt", "url": SELAWIK_LICENSE_URL, "sha256": _sha256(data)})

    found = {(e["family"], e["weight"]) for e in entries}
    expected = {(f, w) for f, w, _ in FONTSOURCE_FILES} | {v for v in LIBERATION_MEMBERS.values() if v} | set(
        SELAWIK_MEMBERS.values()
    )
    missing = expected - found
    if missing:
        raise SystemExit(f"missing font files after download: {sorted(missing)}")

    entries.sort(key=lambda e: (e["family"], e["weight"]))
    lock = {"fontsource_version": FONTSOURCE_VERSION, "fonts": entries, "licenses": licenses}
    with open(LOCK_PATH, "w", encoding="utf-8") as f:
        json.dump(lock, f, indent=2)
        f.write("\n")
    return lock


def verify() -> bool:
    with open(LOCK_PATH, encoding="utf-8") as f:
        lock = json.load(f)
    ok = True
    for entry in lock["fonts"] + lock["licenses"]:
        path = os.path.join(FONTS_DIR, entry["file"])
        if not os.path.exists(path):
            print(f"MISSING {entry['file']}")
            ok = False
            continue
        with open(path, "rb") as f:
            digest = _sha256(f.read())
        if digest != entry["sha256"]:
            print(f"HASH MISMATCH {entry['file']}")
            ok = False
    return ok


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        ok = verify()
        print("fonts verified" if ok else "font verification FAILED")
        sys.exit(0 if ok else 1)
    lock = fetch()
    print(f"wrote {LOCK_PATH}: {len(lock['fonts'])} font files, {len(lock['licenses'])} license files")


if __name__ == "__main__":
    main()
