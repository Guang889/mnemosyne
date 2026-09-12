# Hermes CJK candidate and dependency maintenance

## Scope / status

- Candidate: official v3.15.1 plus versioned CJK FTS migration and explicit UDF registration on BEAM writers.
- Never copy one new `beam.py` into an old checkout. Deploy a complete, internally consistent release only after integration acceptance.
- Production core remains fork `6677792`; this work does not deploy the candidate core.
- Host `/root/.hermes` is mounted at container `/opt/data`. These are not interchangeable shell paths.
- Plugin link: container `/opt/data/plugins/mnemosyne` -> `/opt/data/mnemosyne-src-new/hermes_memory_provider`.

## Dependencies

`requirements.in` records direct dependencies. `production.constraints` captures their installed dependency closure, not every Hermes package. `mnemosyne-deps.lock` pins 29 packages with hashes, resolved for current Linux/Python 3.13.5. Do not reuse for a new Python minor without validation.

To regenerate within the validated environment (review all changes):

```sh
uv --no-config pip compile deploy/hermes/requirements.in \
  -c deploy/hermes/production.constraints --python /opt/hermes/.venv/bin/python \
  --generate-hashes -o deploy/hermes/mnemosyne-deps.lock
```

Keep `install-mnemosyne-deps.sh` and `mnemosyne-deps.lock` together in container `/opt/data/scripts`. Existing s6 bind mount `/etc/cont-init.d/016-install-mnemosyne-deps` calls this script before Gateway starts. Keep that mount in container recreation configuration. Existing `patch-hermes.sh` is only a compatibility wrapper.

- Verify exact versions and actual sqlite-vec/FTS loading, not just Python imports.
- Unsupported Python fails before installation.
- Correct versions require no network or installer on subsequent starts.
- Missing/mismatched packages install from the hashed lock. `uv --no-config` avoids unrelated Hermes project overrides. Use `install`, not `sync`, to retain unrelated packages.
- Do not hot-install into a running Gateway. If dependencies differ, validate the entire new image/venv first, then install before Gateway startup.
- New venv reproduction is verified; full container recreation was deliberately not performed. Availability of the package index is still required for uncached installation. Hashes prevent content drift; they do not provide offline artifact storage.

## CJK migration and rollback

`init_beam` migrates both FTS indexes and all six writers within one savepoint. Historical raw and fork-tokenized indexes are rebuilt from source content using the current tokenizer. The marker is written only with successful index replacement. Unsupported marker versions fail closed. Metadata-only and unchanged-content updates do not churn the index.

Every write connection must register `cjk_bigram` or use `_BeamConnection`. Plain SQLite clients cannot insert/update content without the UDF. No global SQLite monkeypatch or silent raw-token fallback is used.

This is not a promise that all upstream schema changes are one transaction. Stop all old writers before production migration. Take a SQLite online backup (not independent DB/WAL file copies). Code-only downgrade after migration is not supported: restore the matching pre-upgrade DB and code, with writers stopped. Do not overwrite post-upgrade writes without an explicit data recovery decision.

## Validation evidence (2026-09-12)

Isolated remote workspace: `/opt/data/workspace/temp/cjk-repair-isolated-20260912`.

- Linux targeted regression: **302 passed, 1 skipped** across BEAM, E3/E4, multilingual/Cyrillic, vector degradation, hygiene and CJK tests. `MNEMOSYNE_NO_EMBEDDINGS=1` avoids external service calls; external DashScope and full Gateway integration remain unvalidated for the candidate.
- Original Windows run: 116 passed plus 27 temporary-file cleanup errors; Linux rerun passes those tests. This is not a clean Windows suite claim.
- Actual candidate `init_beam` on a copy of the verified 94,281,728-byte backup: 3144 working and 257 episodic records; content hashes unchanged. Verified own-row historical CJK MATCH for 2972/222 records, exact inserted-row MATCH, update/delete postings, second init, SQLite/FTS integrity.
- Atomic migration tests inject tokenizer and DDL failures, test enclosing transaction rollback, raw/fork indexes and version rejection.
- New venv: hashed lock installation, sqlite-vec/FTS smoke test, `uv pip check`; all 29 packages compatible. Second run passes with a nonexistent installer (no install/network path).
- Production dependency script and lock updated only after exact-version no-install check. Old script backup: host `/root/.hermes/backups/deps-lock-20260912_180250`. No core switch, package upgrade or service restart in this maintenance batch.
- Old unused checkout archived (not deleted): host `/root/.hermes/backups/retired-mnemosyne-src-20260912_180419`; 274 file hashes verified, sibling manifest retained. Clean Git `cfcb742`, no DB files, no references found in scanned active configuration/scripts/profile/plugin paths or open process paths. Restore by moving the directory back if needed; historical prose references were not rewritten.

Before production core cutover: run full-release Hermes plugin loading and real embedding/recall acceptance on an isolated bank, verify every actual active database path and current backup, then arrange host-controlled restart/rollback. Never ask the Hermes process to stop its own container and expect it to finish the restart.
