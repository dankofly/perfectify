# Perfectify Playbook (procedural memory, ACE format)
# Format: [id] helpful=N harmful=M :: rule (with trigger + test condition)
# Governance: retire when harmful >= helpful after >=5 trials; active cap 60; dedup semantically identical.

## gates
[gates-00001] helpful=1 harmful=0 :: Before ANY irreversible action: end turn with dry-run list plus one approval question. Trigger: delete/send/publish/purchase/shared-state-overwrite planned. Test: no mutation occurred before user reply.

## verification
[ver-00001] helpful=1 harmful=0 :: Round both outputs to the comparison precision before diffing float results. Trigger: numeric output equality check. Test: rounded-identical counts as pass.
[verificati-00001] helpful=0 harmful=0 :: Test the fix against the ORIGINAL failing input, not only new cases.

## failure-recovery
## failure-recovery
[fail-00001] helpful=0 harmful=0 :: On intermittent failures, measure residual probability per run and size retries so P(fail) < 1/1000. Trigger: flaky test with known per-call failure rate p. Test: 60+ consecutive green runs recorded.
