# Perfectify Playbook (procedural memory, ACE format)
# Format: [id] helpful=N harmful=M :: rule (with trigger + test condition)
# Governance: retire when harmful >= helpful after >=5 trials; active cap 60; dedup semantically identical.

## gates
[gates-00001] helpful=3 harmful=0 :: Before ANY irreversible action: end turn with dry-run list plus one approval question. Trigger: delete/send/publish/purchase/shared-state-overwrite planned. Test: no mutation occurred before user reply.
[gates-00002] helpful=1 harmful=0 :: Before bulk deletion, produce a machine-checked dry-run with counts, cutoff boundary, and edge-case check (near-threshold records kept). Trigger: batch mutation of records. Test: dry-run output lists exact target count and at least one boundary case before any write.

## verification
[ver-00001] helpful=1 harmful=0 :: Round both outputs to the comparison precision before diffing float results. Trigger: numeric output equality check. Test: rounded-identical counts as pass.
[verificati-00001] helpful=0 harmful=0 :: Test the fix against the ORIGINAL failing input, not only new cases.
[verificati-00002] helpful=0 harmful=0 :: Verify selection criteria against both directions: targets matched AND near-miss records confirmed kept. Trigger: filter-based destructive operation. Test: kept-side sample inspected, not only deleted side.
[verificati-00003] helpful=0 harmful=0 :: Prove 'no slowdown' with a matched timing comparison against the un-fixed path (same run count, same machine), reporting overhead per run in ms, not just total wall time. Trigger: performance-nonregression claim for a fix that adds retries/backoff. Test: measured delta vs no-fix baseline is reported and negligible relative to suite time.

## failure-recovery
[fail-00001] helpful=1 harmful=0 :: On intermittent failures, measure residual probability per run and size retries so P(fail) < 1/1000. Trigger: flaky test with known per-call failure rate p. Test: 60+ consecutive green runs recorded.
[failure-re-00001] helpful=0 harmful=0 :: Verify a pre-existing fix instead of trusting it: when the handed-off workspace already contains candidate changes, re-derive the root cause from measured evidence (e.g. per-call failure rate over N calls) and re-run full acceptance. Trigger: task dir missing or already partially fixed. Test: root-cause measurement plus fresh 20+ green runs recorded, not inherited claims.

## governance
[govern-00001] helpful=0 harmful=0 :: Reject benchmark/task-specific bullets at ADD time; a rule naming specific ports, repos, or datasets violates generalization. Trigger: proposed bullet references concrete environment specifics. Test: bullet text contains no environment-unique identifiers.
