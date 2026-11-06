# Look up Flowintel cases from MISP

The `flowintel` enrichment module in [MISP/misp-modules](https://github.com/MISP/misp-modules)
checks whether a MISP attribute value already appears in a Flowintel case and
returns a link to each matching case. Deploy a Flowintel version containing
`POST /api/case/search/attribute` before enabling the module.

Install the updated misp-modules package in the environment running the module
service and restart that service. In MISP's plugin settings, enable the
enrichment service and `Plugin.Enrichment_flowintel_enabled`, then configure:

| Setting | Value |
| --- | --- |
| `Plugin.Enrichment_flowintel_url` | Flowintel application root, e.g. `https://flowintel.example.org` (include a deployment subpath if used; omit `/api`) |
| `Plugin.Enrichment_flowintel_apikey` | API key of a Flowintel user with access to the cases to check |
| `Plugin.Enrichment_flowintel_verify_ssl` | `true` (default); `false` for deployments explicitly requiring disabled certificate verification |
| `Plugin.Enrichment_flowintel_timeout` | Positive request timeout in seconds (default `30`) |

Run **Enrich** on a supported MISP attribute and select **Flowintel case lookup**.
Each hit produces a `link` attribute with the case title in its comment and
`to_ids=false`. An empty result means no matching case is visible to the API user.
Only the selected attribute value is submitted to Flowintel.

The lookup searches standalone attributes and attributes inside MISP objects.
It uses equality under the database's collation, across attribute types, and
includes completed cases. It does not search case titles, notes, or descriptions.
Composite values such as `filename|sha256` are queried as a whole. The API user's
usual case visibility rules apply: public cases, private cases shared with their
organisation, and all cases for administrators. Choose the API user accordingly,
since its case links and titles will be returned to MISP users of the module.

## API contract

Send JSON to `POST /api/case/search/attribute` with an `X-API-KEY` header:

```json
{"value": "example.org"}
```

The endpoint requires an authenticated API user, including read-only users, and
does not modify cases. It returns each matching case once:

```json
{"cases": [{"id": 42, "uuid": "963324e0-0154-4748-93bd-01811e306c72", "title": "Domain investigation", "completed": false}]}
```

An empty match returns HTTP 200 with `{"cases": []}`. Missing, blank, non-string,
or malformed input returns HTTP 400. Missing or invalid API keys return HTTP 403.
The case's browser URL is `<application-root>/case/<id>`.
