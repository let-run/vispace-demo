#!/usr/bin/env python3
"""Add the sample inventory and public CLN17 board to a static ViSpace build."""

import argparse
import json
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import urlopen

REVISION = "2fbd6580de62dd0a331a68c20a7054889c90c6c0"
REPOSITORY = "creapunk/CLN-ClosedLoopNemaDriver"
PROJECT = "hardware/CLN17/V2.5 [NRFND]"
STEM = "CLN17-V2.5"
DEMO = Path(__file__).resolve().parent
SEED = DEMO / "inventory.json"

KICAD_MODELS = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels")
KICAD_SOURCE = "https://gitlab.com/kicad/libraries/kicad-packages3D"
KICAD_LICENSE = f"{KICAD_SOURCE}/-/raw/10.0.0/LICENSE.md"
CLN17_RAW = f"https://raw.githubusercontent.com/{REPOSITORY}/{REVISION}"


def download(url):
    with urlopen(url, timeout=60) as response:
        return response.read()


def fetch(path):
    return download(f"{CLN17_RAW}/{quote(path)}").decode("utf-8")


def bundle_models(demo, board, kicad_models):
    models = demo / "models"
    entries = {}
    missing = []
    for original in sorted(set(re.findall(r'\(model\s+"([^"\\]+)"', board))):
        if original.startswith("kicad-embed://"):
            continue
        library = re.fullmatch(r"\$\{KICAD\d+_3DMODEL_DIR\}/(.+)", original)
        if library:
            source = "kicad"
            path = PurePosixPath(library[1])
        elif original.startswith("${KIPRJMOD}/"):
            source = "cln17"
            path = PurePosixPath(original.removeprefix("${KIPRJMOD}/"))
        else:
            missing.append(original)
            continue
        if path.is_absolute() or ".." in path.parts or path.suffix.lower() not in {".step", ".stp", ".wrl"}:
            missing.append(original)
            continue

        candidates = [path]
        if path.suffix.lower() == ".wrl":
            candidates = [path.with_suffix(".step"), path.with_suffix(".stp"), path]
        for candidate in candidates:
            if source == "kicad":
                local = kicad_models / candidate
                if not local.is_file():
                    continue
                payload = local.read_bytes()
            else:
                try:
                    payload = download(f"{CLN17_RAW}/{quote(f'{PROJECT}/{candidate}')}")
                except HTTPError as error:
                    if error.code != 404:
                        raise
                    continue
            destination = PurePosixPath(source) / candidate
            target = models / destination
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            entries[original] = destination.as_posix()
            break
        else:
            missing.append(original)

    models.mkdir(exist_ok=True)
    if any(path.startswith("kicad/") for path in entries.values()):
        (models / "KICAD-LICENSE.md").write_bytes(download(KICAD_LICENSE))
    (models / "manifest.json").write_text(json.dumps({
        "project": f"{STEM}.kicad_pro",
        "files": entries,
    }, indent=2) + "\n", encoding="utf-8")
    (models / "README.md").write_text(
        "Component models bundled for the CLN17 demo\n\n"
        f"Official KiCad 3D models from the locally installed library: {KICAD_SOURCE}\n"
        "KiCad library contributors, CC BY-SA 4.0 with KiCad's library exception.\n"
        "See KICAD-LICENSE.md for the license when KiCad models are included.\n\n"
        f"CLN17 project models from the public snapshot: https://github.com/{REPOSITORY}/tree/{REVISION}/{quote(PROJECT)}\n"
        "See ../CLN17-LICENSE.md for the upstream project license and attribution.\n",
        encoding="utf-8",
    )
    print(f"Bundled {len(entries)} model references")
    for path in missing:
        print(f"Model unavailable: {path}")


def seed_site(site, kicad_models):
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
    bundle_models(demo, files[f"{STEM}.kicad_pcb"], kicad_models)
    index.write_text(
        html.replace("<title>ViSpace</title>", f"{marker}\n<title>ViSpace Demo</title>"),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path, nargs="?", help="seed an existing build instead")
    parser.add_argument("--kicad-models", type=Path, default=KICAD_MODELS,
                        help="KiCad 3D model library directory")
    args = parser.parse_args()
    if args.site is not None:
        seed_site(args.site, args.kicad_models)
        print(f"Demo site: {args.site.resolve()}")
        return

    build = DEMO.parent / "script" / "web.sh"
    if not build.is_file():
        parser.error("Run this script from the demo folder inside the ViSpace checkout")
    site = DEMO / "site"
    with TemporaryDirectory(dir=DEMO, prefix=".building-") as staging:
        prepared = Path(staging) / "site"
        subprocess.run([str(build), "--build-only", "--output-dir", str(prepared)], check=True)
        seed_site(prepared, args.kicad_models)
        if site.exists():
            shutil.rmtree(site)
        prepared.rename(site)
    print(f"Demo site ready to commit: {site}")


if __name__ == "__main__":
    main()
