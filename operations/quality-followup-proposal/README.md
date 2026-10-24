# Proposed quality follow-up transaction

Not adopted. This plan combines 26 independently reviewed description-only removals of unrelated NSIDC references with one May canonical replacement and two May retirements. It performs no writes. Public catalog 995 -> 993; deployed catalog 1008 -> 1006 with all 13 private models unchanged. Counts are consequences of removing redundancy, not targets.

All 29 distinct targets bind exact old bytes, replacement bytes and archives. The 26 metadata changes preserve every field except the reviewed description sentence; existing source caveats remain. The May canonical retains all three reference defaults through existing parameter/edit/run/scenario paths, with honest limitations and old-ID/output migration notes in docs/MAY-MODEL-MIGRATION.md. Retired IDs do not automatically redirect.

Before execution: obtain final May canonical exact-hash rereview; publish the user-facing migration document; ship export fix 72cef78 in this future quality release, separately from PR7 sensitivity; revalidate current baseline hashes and public/private identity inventory; use the existing reviewed transaction machinery with backup/rollback and hash-bound staged receipts. Preserve all other models and database bytes. Exercise all three defaults plus export refusal and existing comparison controls. This proposal does not authorize execution.

Run the sibling check_plan.py for a read-only exact-source/baseline/metadata validation. It never applies a transaction.
