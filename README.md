# Deploy the ViSpace browser demo

The demo uses its own GitHub Pages repository and hostname. It builds the same
ViSpace WASM application, then adds a sample inventory and an unmodified public
CLN17 V2.5 KiCad project, schematic, and PCB. The source is pinned in
`prepare_web_demo.py`. The bundled design is by Anton Khrustalev /
CREAPUNK under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
The deployed build includes the upstream license and source link at
`/demo/CLN17-LICENSE.md`.

From the ViSpace repository root, run:

```sh
python3 demo/prepare_web_demo.py
```

This builds the current local ViSpace checkout and stages the finished demo in
`demo/site/`. It replaces the previous site only after the build and demo
preparation succeed. Commit the generated site and push `main` from this
demo repository:

```sh
git -C demo add .
git -C demo commit -m "Update ViSpace demo"
git -C demo push -u origin main
```

The remote for this repository is `git@github.com:let-run/vispace-demo.git`.
The workflow deploys the committed `site/` on pushes to `main`. You can also
run it manually from **Actions → Deploy ViSpace demo**.

In the demo repository, set **Settings → Pages → Source** to **GitHub Actions**
and the custom domain to `demo.vispace.let.run`. In the `let.run` DNS zone,
add a CNAME for `demo.vispace` pointing to `let-run.github.io`. Enable
**Enforce HTTPS** after GitHub issues the certificate.

Each browser gets its own copy of the inventory on first launch. Edits survive
reloads. Use **Preferences → General → Reset demo…** to clear the demo and
restore the sample data. The demo uses storage scoped to its hostname.

## Preview locally

After staging the demo, serve it from the ViSpace repository root:

```sh
python3 script/serve_web.py --directory demo/site --port 8788 --http
```

## 3D models

The demo build downloads the referenced project models from the pinned public
CLN17 snapshot and copies the referenced standard models from the local KiCad
library. On macOS it looks in
`/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels` by default.
For another installation, pass its library directory explicitly:

```sh
python3 demo/prepare_web_demo.py --kicad-models /path/to/3dmodels
```

The generated `site/demo/models/` directory contains the model manifest,
files, and attribution. Visitors fetch these models when they open **3D board**.
Build output lists references it could not resolve, including paths pointing
to the board author's machine.
