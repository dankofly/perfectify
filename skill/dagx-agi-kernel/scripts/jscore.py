#!/usr/bin/env python3
"""What is verification actually worth against what it costs.

Asked on r/codex: does a kernel like this get agents stuck in evidentiary loops,
rerunning big suites for a one-line change. `redteam-07` tests that it does not
escalate. It does not answer the harder question, which is what an extra dollar
or an extra minute of verification is worth in the first place.

This is a faithful port of the J-score from the sibling research repo,
`benchmarks/metrics/jscore.js` in github.com/dankofly/dagx:

    J = w_q*quality + w_r*(1-risk) + w_c*(1-cost/maxCost) + w_l*(1-latency/maxLatency)

Read the next paragraph before you use any number this prints.

**The weights and ceilings are a policy, not a measurement.** Nobody measured
that quality is worth 0.5 and latency 0.15. Somebody chose it. The defaults are
DAGx's and are carried over unchanged so results stay comparable between the two
repos, and every one of them is overridable. What this tool does is make the
consequences of that choice explicit, because a weight vector you picked casually
silently fixes the price of everything.

    python3 jscore.py --explain
    python3 jscore.py --score --quality 0.86 --cost-usd 0.015 --latency-ms 8000
    python3 jscore.py --breakeven --cost-usd 0.06 --latency-ms 15000 \
                      --vs-cost-usd 0.015 --vs-latency-ms 8000
    python3 jscore.py --self-test

The exchange rates `--explain` prints are arithmetic on the weights, not
findings. The self-test proves them, so they are checkable rather than claimed.
"""

from __future__ import annotations

import argparse
import json
import sys

# Ported unchanged from DAGx benchmarks/metrics/jscore.js DEFAULT_WEIGHTS.
DEFAULT_WEIGHTS = {"quality": 0.5, "risk": 0.15, "cost": 0.20, "latency": 0.15}
DEFAULT_MAX_COST_USD = 0.10
DEFAULT_MAX_LATENCY_MS = 30_000


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return min(max(x, lo), hi)


def jscore(quality: float, risk: float, cost_usd: float, latency_ms: float,
           weights: dict[str, float], max_cost: float, max_latency: float) -> dict:
    q = clamp(quality)
    r = clamp(risk)
    norm_cost = clamp(cost_usd / max_cost) if max_cost > 0 else 1.0
    norm_latency = clamp(latency_ms / max_latency) if max_latency > 0 else 1.0
    parts = {
        "quality": weights["quality"] * q,
        "risk": weights["risk"] * (1 - r),
        "cost": weights["cost"] * (1 - norm_cost),
        "latency": weights["latency"] * (1 - norm_latency),
    }
    return {
        "j": round(clamp(sum(parts.values())), 6),
        "components": {k: round(v, 6) for k, v in parts.items()},
        "normalized": {"cost": round(norm_cost, 6), "latency": round(norm_latency, 6)},
        "saturated": [name for name, value in
                      (("cost", norm_cost), ("latency", norm_latency)) if value >= 1.0],
    }


def exchange_rates(weights: dict[str, float], max_cost: float,
                   max_latency: float) -> dict:
    """Derived from the weights by division. Not measured, not a finding.

    Quality is expressed on a 100-point scale because "4 quality points" is
    easier to argue about than "0.04 of J".
    """
    per_quality_point = weights["quality"] / 100.0
    cent = weights["cost"] * (0.01 / max_cost) if max_cost > 0 else float("inf")
    second = weights["latency"] * (1000.0 / max_latency) if max_latency > 0 else float("inf")
    ten_pp_risk = weights["risk"] * 0.10
    return {
        "one_cent_of_cost_equals_quality_points": round(cent / per_quality_point, 3),
        "one_second_of_latency_equals_quality_points": round(second / per_quality_point, 3),
        "ten_points_of_risk_equals_quality_points": round(ten_pp_risk / per_quality_point, 3),
        "note": ("Division on the weights, nothing empirical. Change a ceiling "
                 "and these move: the ceilings are the routing policy."),
    }


def breakeven(cost_a: float, latency_a: float, cost_b: float, latency_b: float,
              weights: dict[str, float], max_cost: float, max_latency: float,
              quality_b: float | None = None) -> dict:
    """How much better must A be, in quality, to beat B at equal risk.

    Reachability is NOT a property of the gap alone. A gap of 0.25 is ordinary
    unless B is already scoring 0.85, in which case A would need 1.10 and quality
    is capped at 1.0. So without B's measured quality this reports the gap and
    declines to rule on whether it can be closed. An earlier version of this
    function ruled anyway; its own self-test caught it.
    """
    def overhead(cost: float, latency: float) -> float:
        return (weights["cost"] * (1 - clamp(cost / max_cost))
                + weights["latency"] * (1 - clamp(latency / max_latency)))

    deficit = overhead(cost_b, latency_b) - overhead(cost_a, latency_a)
    needed_delta = deficit / weights["quality"] if weights["quality"] else float("inf")
    out = {
        "quality_advantage_A_needs": round(needed_delta, 6),
        "quality_b_used": quality_b,
    }
    if quality_b is None:
        out["reachable"] = None
        out["reading"] = (
            f"A must score {round(needed_delta, 4)} higher in quality than B. "
            f"Whether that is reachable depends on B's measured quality, which "
            f"was not supplied: pass --vs-quality. Insufficient data to verify."
        )
        return out

    required = clamp(quality_b, 0.0, 10.0) + needed_delta
    out["quality_A_required"] = round(required, 6)
    out["reachable"] = required <= 1.0
    out["reading"] = (
        f"B scores {quality_b}, so A must reach {round(required, 4)}. " + (
            "Reachable." if required <= 1.0 else
            f"Not reachable: quality is capped at 1.0, so under this policy A "
            f"can never win, whatever model it runs. Raise maxCost or "
            f"maxLatency if that is the wrong call."
        )
    )
    return out


def self_test() -> int:
    failures: list[str] = []
    w, mc, ml = DEFAULT_WEIGHTS, DEFAULT_MAX_COST_USD, DEFAULT_MAX_LATENCY_MS

    # Bounds.
    if jscore(1, 0, 0, 0, w, mc, ml)["j"] != 1.0:
        failures.append("perfect run should score 1.0")
    if jscore(0, 1, 10, 10 ** 9, w, mc, ml)["j"] != 0.0:
        failures.append("worst run should score 0.0")
    if not 0.0 <= jscore(0.5, 0.5, 0.05, 15000, w, mc, ml)["j"] <= 1.0:
        failures.append("J escaped [0,1]")

    # Monotonicity in each signal, holding the rest fixed.
    base = jscore(0.8, 0.2, 0.03, 9000, w, mc, ml)["j"]
    if jscore(0.9, 0.2, 0.03, 9000, w, mc, ml)["j"] <= base:
        failures.append("more quality did not raise J")
    if jscore(0.8, 0.2, 0.06, 9000, w, mc, ml)["j"] >= base:
        failures.append("more cost did not lower J")
    if jscore(0.8, 0.2, 0.03, 20000, w, mc, ml)["j"] >= base:
        failures.append("more latency did not lower J")
    if jscore(0.8, 0.4, 0.03, 9000, w, mc, ml)["j"] >= base:
        failures.append("more risk did not lower J")

    # The three exchange rates DAGx states in prose are derivable. Prove them
    # rather than repeating them.
    rates = exchange_rates(w, mc, ml)
    for key, want in (("one_cent_of_cost_equals_quality_points", 4.0),
                      ("one_second_of_latency_equals_quality_points", 1.0),
                      ("ten_points_of_risk_equals_quality_points", 3.0)):
        if abs(rates[key] - want) > 1e-6:
            failures.append(f"{key}: expected {want}, derived {rates[key]}")

    # And check the rate against the formula directly, so the derivation cannot
    # drift away from what jscore() actually does.
    a = jscore(0.80, 0, 0.02, 0, w, mc, ml)["j"]
    b = jscore(0.80, 0, 0.03, 0, w, mc, ml)["j"]
    if abs((a - b) - (w["quality"] * 0.04)) > 1e-9:
        failures.append("one cent of cost is not worth 4 quality points in practice")

    # DAGx's stated consequence, reproduced exactly: against a $0.015/8s profile
    # scoring 0.85, a $0.06/15s profile would need quality 1.10.
    be = breakeven(0.06, 15000, 0.015, 8000, w, mc, ml, quality_b=0.85)
    if abs(be["quality_advantage_A_needs"] - 0.25) > 1e-6:
        failures.append(f"expected a 0.25 quality gap, got {be['quality_advantage_A_needs']}")
    if abs(be["quality_A_required"] - 1.10) > 1e-6:
        failures.append(f"expected required quality 1.10, got {be['quality_A_required']}")
    if be["reachable"]:
        failures.append("1.10 is above the cap, so it must not be reachable")
    # The same gap against a weaker B is ordinary, which is why the gap alone
    # cannot carry the verdict.
    if not breakeven(0.06, 15000, 0.015, 8000, w, mc, ml, quality_b=0.5)["reachable"]:
        failures.append("a 0.25 gap over a 0.5 baseline should be reachable")
    # Without B's quality there is no verdict to give.
    if breakeven(0.06, 15000, 0.015, 8000, w, mc, ml)["reachable"] is not None:
        failures.append("no quality_b should mean no reachability verdict")
    # Raising the ceiling must reopen it, which is the point of calling the
    # ceilings a policy rather than a detail.
    if not breakeven(0.06, 15000, 0.015, 8000, w, 0.50, ml, quality_b=0.85)["reachable"]:
        failures.append("raising maxCost should make the frontier profile reachable")

    # Saturation is reported, not hidden: beyond the ceiling, more cost is free.
    hot = jscore(0.8, 0, 0.5, 60000, w, mc, ml)
    if hot["saturated"] != ["cost", "latency"]:
        failures.append("saturated dimensions not reported")
    if hot["j"] != jscore(0.8, 0, 5.0, 600000, w, mc, ml)["j"]:
        failures.append("past the ceiling, further cost should not change J")

    for line in failures:
        print(line, file=sys.stderr)
    total = 18
    print(f"self-test: {total - len(failures)}/{total} checks passed")
    return 1 if failures else 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--explain", action="store_true",
                   help="print the exchange rates the current policy implies")
    p.add_argument("--score", action="store_true")
    p.add_argument("--breakeven", action="store_true")
    p.add_argument("--quality", type=float)
    p.add_argument("--risk", type=float, default=0.0)
    p.add_argument("--cost-usd", type=float)
    p.add_argument("--latency-ms", type=float)
    p.add_argument("--vs-cost-usd", type=float)
    p.add_argument("--vs-quality", type=float,
                   help="B's measured quality; without it reachability is not ruled on")
    p.add_argument("--vs-latency-ms", type=float)
    p.add_argument("--max-cost-usd", type=float, default=DEFAULT_MAX_COST_USD)
    p.add_argument("--max-latency-ms", type=float, default=DEFAULT_MAX_LATENCY_MS)
    for name in DEFAULT_WEIGHTS:
        p.add_argument(f"--w-{name}", type=float, default=DEFAULT_WEIGHTS[name])
    args = p.parse_args()

    if args.self_test:
        return self_test()

    weights = {name: getattr(args, f"w_{name}") for name in DEFAULT_WEIGHTS}
    total = sum(weights.values())
    policy = {
        "weights": weights, "max_cost_usd": args.max_cost_usd,
        "max_latency_ms": args.max_latency_ms,
        "source": "DAGx benchmarks/metrics/jscore.js, defaults unchanged",
        "status": "policy choice, not a measured optimum",
    }
    if abs(total - 1.0) > 1e-9:
        policy["warning"] = (f"weights sum to {round(total, 6)}, not 1.0, so J is "
                             f"no longer bounded at 1 and the exchange rates shift")

    if args.explain:
        print(json.dumps({"policy": policy,
                          "exchange_rates": exchange_rates(weights, args.max_cost_usd,
                                                           args.max_latency_ms)},
                         indent=2, sort_keys=True))
        return 0

    if args.breakeven:
        missing = [n for n, v in (("--cost-usd", args.cost_usd),
                                  ("--latency-ms", args.latency_ms),
                                  ("--vs-cost-usd", args.vs_cost_usd),
                                  ("--vs-latency-ms", args.vs_latency_ms)) if v is None]
        if missing:
            print(f"Insufficient data to verify: missing {', '.join(missing)}",
                  file=sys.stderr)
            return 2
        print(json.dumps({"policy": policy,
                          "breakeven": breakeven(args.cost_usd, args.latency_ms,
                                                 args.vs_cost_usd, args.vs_latency_ms,
                                                 weights, args.max_cost_usd,
                                                 args.max_latency_ms, args.vs_quality)},
                         indent=2, sort_keys=True))
        return 0

    if args.score:
        # A score built from guesses is worse than no score, so it refuses.
        missing = [n for n, v in (("--quality", args.quality),
                                  ("--cost-usd", args.cost_usd),
                                  ("--latency-ms", args.latency_ms)) if v is None]
        if missing:
            print(f"Insufficient data to verify: missing {', '.join(missing)}. "
                  f"Measure them; do not estimate them.", file=sys.stderr)
            return 2
        out = jscore(args.quality, args.risk, args.cost_usd, args.latency_ms,
                     weights, args.max_cost_usd, args.max_latency_ms)
        out["policy"] = policy
        out["caveat"] = ("A single J is only meaningful against another J computed "
                         "under the same policy on matched tasks.")
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0

    p.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
