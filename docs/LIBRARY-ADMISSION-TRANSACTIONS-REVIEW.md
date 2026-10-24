# Independent review: library admission transactions

Reviewed October 24, 2026. **Approved for the documented explicit-manifest Linux/POSIX operator workflow**, at the exact source hashes below. This review does not authorize applying a manifest or deploying changes.

Reviewed `scripts/curate_library.py`, `tests/test_curation_deployment.py` and `docs/LIBRARY-ADMISSION-TRANSACTIONS.md`. I changed this review document and removed trailing blank lines from the reviewed script for the release formatting check; executable content is unchanged. All execution checks used temporary model trees, mocked service commands or read-only source inspection; active models and production data were untouched.

## Findings resolved before approval

Three concrete issues were reported to the implementation owner and corrected:

1. **Unreadable inventory subtree could hide an existing identity.** The initial os.walk omitted onerror, so an injected PermissionError on models/hidden silently skipped an existing duplicate identity and allowed a create plan. The final shared model_files walker raises traversal errors. Both identity inventory and data snapshots fail closed. A focused regression covers both paths.
2. **Uppercase JSON was inventoried for IDs but omitted from preservation hashes.** The initial data_hashes used a lowercase glob. The final implementation uses the same case-insensitive JSON walk as identity inventory. A foreign edit to legacy.JSON now prevents a success receipt, preserves the foreign edit and rolls back the transaction's own created file.
3. **Restrictive umask made a newly created category inaccessible despite mode0644 model bytes.** A direct probe with umask077 produced a new directory of mode0700. Newly created directory descriptors are now explicitly set to0755 after ownership adjustment. The final regression starts with an existing models directory of0750, verifies that mode remains unchanged, checks the new category0755 and file0644.

No unresolved blocker remains within the documented stopped-writer workflow.

## Verified behavior

The final scoped suite passed independently:

```
.venv/bin/pytest -q tests/test_curation_deployment.py
24 passed in 0.24s
```

The tests and inspection establish:

- Dry runs validate the complete action set without stopping a service, creating backups or writing model data.
- Create identity and exact UTF-8 bytes are bound to the declared ID and SHA-256. Invalid JSON, nonfinite JSON constants, BOM content, duplicate create IDs and existing IDs anywhere in the model tree are rejected.
- Destination paths are individual relative JSON files under models. Database paths, traversal, drive/backslash syntax and symlink paths are rejected. Inventory refuses unreadable subtrees, symlinks, malformed JSON and nonregular JSON files; FIFO checks do not block.
- The writer is stopped and the manifest rechecked before mutation. Each create checks identities again. Complete bytes are written/fsynced to an exclusive temporary file and published with a hard link that refuses an already existing destination.
- Parent traversal uses O_DIRECTORY/O_NOFOLLOW descriptors; injected symlink substitution cannot redirect the new file outside models.
- Successful publication is recorded before temporary-file cleanup/fsync. An injected cleanup failure therefore still rolls back the published file.
- Mixed retire/replace/create transactions preserve original backups. Unrelated model hashes and models.db are checked; the database is never restored, replaced or deleted.
- Failure removes a created file only when its current hash still matches that transaction's payload. A subsequently changed file is preserved and reported as refused rollback. Other eligible actions are still restored.
- A preexisting backup is never reused or modified. Backup ownership tracking prevents writing a rollback receipt into someone else's prior backup.
- Final receipts list exact created IDs/paths/hashes and expected data hashes. Existing file/directory modes are preserved where documented; newly created model bytes and parent directory access modes are explicit.

## Operational boundaries

This is an explicit, reviewed-manifest transaction, not directory synchronization or scientific admission review. The identity/content checks do not replace model-schema validation, numerical verification, provenance review or independent candidate approval.

Stopping the configured service and checking before/after data reduces races but does not lock out unrelated writers. Atomic no-overwrite publication specifically protects create destinations. Existing retire/replace actions retain their pre/post hash-based operator contract; this review does not claim atomic compare-and-swap against an uncooperative concurrent writer. The operator must select the actual writer service and control the maintenance window.

A data receipt is not a health check: service restart success and application behavior remain separate release checks. Newly created empty directories can remain after a failed transaction; no recursive cleanup is attempted. This is safer than deleting an unexpectedly populated directory.

## Exact reviewed source hashes

| File | SHA-256 |
| --- | --- |
| scripts/curate_library.py | `93bf565bbe146ef54ad992acd44b2c6785480b556153c8e52732c9b30b287745` |
| tests/test_curation_deployment.py | `4559a2dee16d2ce7ed18efdc2e4555c0d8ea0aef1784acb6e3a6364014f7d8d6` |
| docs/LIBRARY-ADMISSION-TRANSACTIONS.md | `4c035c0140c7af92f357760d6bf6f1d0873cbfdd853cf5b01c9a8e169664859d` |

Approval applies to these bytes and this stated scope. Any substantive source change requires another comparison.
