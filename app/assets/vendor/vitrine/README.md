# Vitrine — Flowtime browser assets

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
