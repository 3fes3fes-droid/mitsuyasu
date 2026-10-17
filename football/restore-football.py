#!/usr/bin/env python3
"""Restore the football source and all original photos from the GitHub archive."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile

ZIP_SHA256 = "e9df5788b15584ee8e22325de81b4cd37d1b957598dec6fae5a8e7a8d643ec44"
SOURCE_URL = "https://raw.githubusercontent.com/3fes3fes-droid/mitsuyasu/main/football/football-latest-source.zip"
ASSET_URL = "https://raw.githubusercontent.com/3fes3fes-droid/mitsuyasu/9e264debfed14ac056b2f1b0bac0a43ba9fc85e3/Football_archive_single.html"

def download(url):
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="football-restored")
    parser.add_argument("--asset-archive", type=Path)
    args = parser.parse_args()
    destination = Path(args.output).resolve()
    if destination.exists() and any(destination.iterdir()):
        raise SystemExit("Choose an empty output directory.")
    local_zip = Path(__file__).with_name("football-latest-source.zip")
    packed = local_zip.read_bytes() if local_zip.exists() else download(SOURCE_URL)
    if hashlib.sha256(packed).hexdigest() != ZIP_SHA256:
        raise SystemExit("Source archive checksum mismatch.")
    with zipfile.ZipFile(io.BytesIO(packed)) as archive:
        for name in archive.namelist():
            path = Path(name)
            if path.is_absolute() or ".." in path.parts:
                raise SystemExit("Unexpected archive path.")
        archive.extractall(destination)
    manifest = json.loads((destination / "football-migration-manifest.json").read_text())
    html = (args.asset_archive.read_bytes() if args.asset_archive else download(ASSET_URL)).decode("utf-8")
    marker = "const ASSETS = "
    position = html.index(marker) + len(marker)
    assets, _ = json.JSONDecoder().raw_decode(html[position:])
    for path, expected in manifest["photos"].items():
        output = destination / path
        if not output.exists():
            asset = assets[path.removeprefix("public/")]
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(base64.b64decode(asset[1], validate=True))
        if hashlib.sha256(output.read_bytes()).hexdigest() != expected:
            raise SystemExit("Photo checksum mismatch: " + path)
    print("Restored source, data and", manifest["photoCount"], "original photos to", destination)

if __name__ == "__main__":
    main()
