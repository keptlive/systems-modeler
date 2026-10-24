# Identifier import repair

The three previously recorded identifier failures are fixed. Quoted `A-B` and
`A_B` remain distinct, U+2002 EN SPACE is preserved inside a quoted name, and an
unquoted internal dollar sign works in identifiers such as `Cash$Balance`.
The original regression assertions now pass without expected-failure markers.

References bind first to an exact declared spelling, then to a unique normalized
identity, then to a unique historical punctuation alias. Normalized identity uses
NFC, case folding, and the existing space/newline/nonbreaking-space/underscore
equivalence. Ambiguous fallback is an error. Binding uses the complete declaration
inventory, so an unresolved exact name cannot accidentally read an already
computed alias. Existing case and standard-whitespace collisions remain errors.

The same rules cover evaluation, initialization, XMILE flow-name mapping, dependency
graphs, lookup tables, reports, units and related analysis. The conservative
execution scheduler retains its fallback for punctuation-alias collisions.
Historical random streams remain unchanged for existing models; newly permitted
distinct names receive separate stream keys. Dollar tokenization preserves source
boundaries and does not join names across spaces or accept a leading dollar sign.

The editor preserves these identities when renaming imported elements. It checks
all references before changing the model and cancels a rename that would change
an unrelated reference's binding. Existing saved model IDs and source names are
preserved; no library definitions are changed by this repair.

## Verification

- All 1,000 public models completed their full default runs. Before/after hashes
  of every time vector, numerical series, report series and effective random seed
  are identical; all 1,000 model-file hashes are also unchanged.
- Permanent regressions cover the original three cases, Unicode identity,
  declaration order, aliases, random streams, flow endpoints, tables, units,
  feedback and JSON/XMILE roundtrips.
- Real file-backed HTTP acceptance imported, fetched, simulated, exported and
  reimported each of the three cases. An actual MCP client simulated all six saved
  imports. These tests used isolated storage.
- Browser acceptance imported a fixture containing all three cases, renamed one
  literal identifier, saved, exported XMILE, reimported and simulated it. The
  distinct values remained 1, 2, 4 and 8; their output remained 15 and the
  accumulated stock ended at 30 after two time units.

This repair does not expand the documented scalar XMILE subset into support for
every XMILE construct. Existing structured-model and solver export restrictions
remain explicit. Historical benchmark receipts predate this repair; no new speed
advantage over Simlin is claimed.
