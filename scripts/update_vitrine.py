#!/usr/bin/env python3
"""Vendor Flowtime's built Vitrine entry; never copy or maintain viewer source here."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

FILES = ("flowtime.js", "flowtime.css", "flowtime.d.ts")


def update(source: Path, build: bool = False) -> None:
    source = source.resolve()
    if build:
        subprocess.run(["npm", "run", "build"], cwd=source, check=True)
    inputs = sorted((source / "src/components/flowtime").rglob("*"))
    inputs = [path for path in inputs if path.is_file()]
    inputs.append(source / "src/entries/flowtime.js")
    artifacts = [source / "dist" / name for name in FILES]
    if not inputs or not all(path.is_file() for path in artifacts):
        raise SystemExit("Vitrine's Flowtime build is missing. Run npm run build in Vitrine, or pass --build.")
    if max(path.stat().st_mtime for path in inputs) > min(path.stat().st_mtime for path in artifacts):
        raise SystemExit("Vitrine sources are newer than dist/. Rebuild Vitrine first, or pass --build.")
    target = Path(__file__).resolve().parents[1] / "app/assets/vendor/vitrine"
    target.mkdir(parents=True, exist_ok=True)
    for path in artifacts:
        shutil.copyfile(path, target / path.name)
    shutil.copyfile(source / "LICENSE", target / "LICENSE")
    package = json.loads((source / "package.json").read_text())
    fingerprint = hashlib.sha256()
    for path in inputs:
        fingerprint.update(str(path.relative_to(source)).encode() + b"\0" + path.read_bytes())
    manifest = {
        "package": "vitrine",
        "version": package["version"],
        "entry": "vitrine/flowtime",
        "source": "https://github.com/DavidCruciani/vitrine",
        "source_sha256": fingerprint.hexdigest(),
        "files": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in artifacts},
    }
    (target / "SOURCE.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (target / "README.md").write_text("""# Vitrine — Flowtime browser assets

These are generated artifacts from Vitrine's `vitrine/flowtime` entry, not a second
copy of the viewer source. The canonical source and tests are in Vitrine:
`src/components/flowtime/`, `tests/flowtime/`, and `tests/unit/flowtime.test.js`.

Only the standalone Flowtime entry is shipped here. It has no runtime dependencies
or remote asset loads. Other Vitrine components can be added independently later.
`SOURCE.json` records the source fingerprint and the exact artifact hashes.

To update from the Flowintel repository root:

```sh
python3 scripts/update_vitrine.py ../vitrine --build
cd app/assets && bun run build:static
```

Normal Flowintel builds use these committed assets and require no sibling checkout
or network. Vite copies the JS to `app/static/js/vendor/vitrine/flowtime.js` and
the CSS to `app/static/css/vendor/vitrine/flowtime.css`.

Flowintel owns its adapter, API calls, permission checks, modals, Graph renderer,
CSRF-protected writes, and saved preferences in `app/static/js/case/`.
Vitrine owns timeline rendering, filtering, selection, actions and custom view
lifecycle. Text size affects Timeline and Combined timeline; feed text stays fixed.

Run `node --test tests/frontend/*.test.mjs` and the timeline Flask regression tests
after refreshing assets. See Vitrine's `docs/components/flowtime.md` for its API.
""")
    print(f"Updated Vitrine {package['version']} Flowtime assets in {target}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Vitrine checkout containing src/ and dist/")
    parser.add_argument("--build", action="store_true", help="Build Vitrine before copying artifacts")
    args = parser.parse_args()
    update(args.source, args.build)
