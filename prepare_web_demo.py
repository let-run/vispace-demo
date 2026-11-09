#!/usr/bin/env python3
"""Add the sample inventory and public CLN17 board to a static ViSpace build."""

import argparse
import json
import shutil
import subprocess
from tempfile import TemporaryDirectory
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

REVISION = "2fbd6580de62dd0a331a68c20a7054889c90c6c0"
REPOSITORY = "creapunk/CLN-ClosedLoopNemaDriver"
PROJECT = "hardware/CLN17/V2.5 [NRFND]"
STEM = "CLN17-V2.5"
DEMO = Path(__file__).resolve().parent
SEED = DEMO / "inventory.json"


def fetch(path):
    url = f"https://raw.githubusercontent.com/{REPOSITORY}/{REVISION}/{quote(path)}"
    with urlopen(url, timeout=60) as response:
        return response.read().decode("utf-8")


def seed_site(site):
    index = site / "index.html"
    html = index.read_text()
    marker = '<meta name="vispace-demo" content="enabled">'
    if marker not in html and html.count("<title>ViSpace</title>") != 1:
        raise ValueError("Expected a built ViSpace index.html")

    data = json.loads(SEED.read_text(encoding="utf-8"))
    files = {
        name: fetch(f"{PROJECT}/{name}")
        for name in (f"{STEM}.kicad_{ext}" for ext in ("pro", "sch", "pcb"))
    }
    license_text = fetch("license.md")
    data["projects"][0]["kicad"] = {
        "path": f"{STEM}.kicad_pro",
        "revision": REVISION,
        "files": files,
    }

    demo = site / "demo"
    demo.mkdir(exist_ok=True)
    (demo / "inventory.json").write_text(json.dumps(data), encoding="utf-8")
    (demo / "CLN17-LICENSE.md").write_text(
        f"Source: https://github.com/{REPOSITORY}/tree/{REVISION}/{quote(PROJECT)}\n\n"
        "The demo includes the original project, schematic and PCB files.\n\n"
        + license_text,
        encoding="utf-8",
    )
    index.write_text(
        html.replace("<title>ViSpace</title>", f"{marker}\n<title>ViSpace Demo</title>"),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path, nargs="?", help="seed an existing build instead")
    args = parser.parse_args()
    if args.site is not None:
        seed_site(args.site)
        print(f"Demo site: {args.site.resolve()}")
        return

    build = DEMO.parent / "script" / "web.sh"
    if not build.is_file():
        parser.error("Run this script from the demo folder inside the ViSpace checkout")
    site = DEMO / "site"
    with TemporaryDirectory(dir=DEMO, prefix=".building-") as staging:
        prepared = Path(staging) / "site"
        subprocess.run([str(build), "--build-only", "--output-dir", str(prepared)], check=True)
        seed_site(prepared)
        if site.exists():
            shutil.rmtree(site)
        prepared.rename(site)
    print(f"Demo site ready to commit: {site}")


if __name__ == "__main__":
    main()
