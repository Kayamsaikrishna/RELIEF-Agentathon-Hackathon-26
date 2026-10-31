# Registry format

`data/registry/registry.json`: `{version, synthetic, note, packages[], hospitals[]}`.

* package: `code, name, specialty, tier (2A|2B|3A|4A), reserved_for_public, required_docs[]` (document kinds as in `DocKind`).
* hospital: `hospital_id, name, type (public|private), state, district, specialties[], empanelment_active`.

Set `"synthetic": false` only for a real, authorised export; the UI warning disappears then. Point `RELIEF_REGISTRY_PATH` at the file.
