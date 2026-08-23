# Trial Ledger

Use one ledger for one baseline/challenger evaluation. Record observed values only. Use `null` when a value was not measured.

## Experiment Contract

| Field | Value |
| --- | --- |
| Evaluation ID | `<id>` |
| Goal and target gap | `<observable gap>` |
| Baseline version | `<version or artifact hash>` |
| Challenger version | `<version or artifact hash>` |
| Model and version | `<exact identifier>` |
| Harness and configuration | `<version and material settings>` |
| Cases and held-out rule | `<dataset version and split rule>` |
| Run order or randomization | `<method>` |
| Acceptance rule | `<ordered must-pass conditions>` |
| Protected behavior | `<regression gates>` |
| Resource contract | `<attempt, token, tool, time, compute, and cost limits>` |
| Evaluator | `<deterministic check or blinded adjudicator>` |

## Trial Records

| Case | Condition | Attempt | Activated | Success | Acceptance evidence | Protected failures | Input tokens | Output tokens | Tool calls | Wall time ms | Cost | Artifact or trace | Notes |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `<case-id>` | `baseline` or `candidate` | 1 | `true`, `false`, or `null` | `true`, `false`, or `null` | `<verifier result>` | 0 | `null` | `null` | `null` | `null` | `null` | `<URI or hash>` | `<material limitation>` |

## Promotion Record

| Decision field | Result |
| --- | --- |
| Activation precision and recall | `<separate values plus denominators>` |
| Paired success delta | `<percentage points plus paired count>` |
| Paired token delta | `<absolute and percent plus paired count>` |
| Protected failures | `<baseline and candidate counts>` |
| Held-out result | `<coverage and result>` |
| Complexity or context delta | `<measured change>` |
| Decision | `promote`, `preserve`, `rollback`, or `insufficient evidence` |
| Decisive evidence | `<artifact, trace, or result hash>` |
| Residual uncertainty | `<unevaluated scope>` |

Do not promote from this template alone. The recorded evidence and evaluation design determine whether an improvement claim is supported.
