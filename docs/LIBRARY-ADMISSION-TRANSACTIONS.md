# Library admission transactions

`scripts/curate_library.py` applies an explicit manifest of 1–200 reviewed actions. Existing `retire` and `replace` actions retain their hash-bound behavior. A `create` action admits one new model without copying or synchronizing a directory.

## Create manifest

```json
{
  "actions": [
    {
      "action": "create",
      "file": "models/reviewed/example.json",
      "id": "example",
      "content": "{\"id\":\"example\"}\n",
      "after_sha256": "SHA256_OF_EXACT_UTF8_CONTENT"
    }
  ]
}
```

`content` must be valid UTF-8 JSON object text with a nonempty string `id` equal to the declared identity. Its exact encoded bytes must match `after_sha256`. Nonfinite JSON constants and a byte-order mark are rejected. This transaction check establishes identity and reviewed bytes; model schema, scientific quality, provenance and admission approval are separate review steps.

The destination must be a relative `.json` path under `models/`. Absolute paths, parent traversal, backslashes, drive syntax and symbolic links are rejected. Both the exact destination and the declared identity must be absent: the identity inventory reads every JSON file, including uppercase extensions, throughout the model tree. An unreadable, malformed, nonregular or symlinked inventory entry prevents creation. Duplicate create identities and duplicate destination actions are rejected. Retirement elsewhere in the same manifest does not make an existing identity eligible for creation; use the existing replacement action for an identity already present.

## Dry run and apply

Run without `--apply` to validate the complete manifest and print planned create destinations:

```sh
python scripts/curate_library.py --app /path/to/app --manifest /path/to/manifest.json --backup /path/to/new-backup --service systems-modeler
```

A dry run does not stop the service, create a backup directory or modify model data. Applying uses the same command with `--apply`. The existing Linux service is stopped, the manifest is checked again, and a new private backup directory is created. Backups inside `models/` or at `models.db` are rejected. An existing backup directory is never reused or modified.

Before each admission, the script checks the identity inventory again. It creates missing parent directories through directory descriptors that refuse symlink traversal. Complete model bytes are written to an exclusive temporary file, flushed and synchronized, then published with an atomic hard link that refuses an existing destination. The model receives mode `0644` and its parent's owner and group. Newly created directories receive mode `0755` and inherit their parent's owner and group; existing directory modes remain unchanged. This requires the script's existing Linux/POSIX deployment environment and sufficient ownership permissions.

After all actions, model JSON and `models.db` hashes must equal the expected transaction result, and created identities are inventoried again. The service restart runs in the existing finalization path. A data receipt confirms data checks, not service health. Stopping the configured writer and rechecking reduces races; this is not a filesystem lock against unrelated concurrent writers.

## Backup, receipt and rollback

The backup contains:

- `manifest.json` and `data-before.json` with the reviewed actions and initial data hashes.
- Original files for retire and replace actions; creates have no original file to back up.
- `created-files.json` listing each planned created path, identity and exact hash.
- `receipt.json` on success, with retired/replaced/created counts, created-file details and resulting data hashes.
- `rollback-receipt.json` on failure after backup creation, listing restored or removed paths and any unexpected edits that prevented rollback.

If a transaction fails, applied actions are reversed. A created file is deleted only if its current bytes still match that transaction's created hash. A foreign or subsequently edited file is preserved and reported as a refused rollback. Rollback continues restoring other eligible actions even when one path has an unexpected edit. Existing retire/replace targets retain their hash guards and original-file backups. The script never restores, replaces or deletes `models.db`; its hash is checked to detect concurrent changes. Unrelated files remain untouched. Newly created empty directories may remain after rollback; there is no recursive directory cleanup.

## Verification

`tests/test_curation_deployment.py` exercises existing retirement/replacement behavior and create validation, duplicate identities, destination races, post-stop rechecks, symlink races, atomic-publication cleanup failures, mixed rollback, foreign edits, database preservation, private backups, regular-file enforcement and restrictive operator umasks. Tests use temporary model trees and mocked service operations; they do not apply admissions to the active library or a production service.
