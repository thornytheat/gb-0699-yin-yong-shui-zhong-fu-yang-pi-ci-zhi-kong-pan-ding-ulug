from app.report import report

PRIORITY = ["BLANK_FAIL", "BLANK_MISSING", "RECOVERY_FAIL", "SPIKE_ZERO",
            "BASE_MISSING", "PAIR_FAIL", "PAIR_MISSING", "CENSORED_REVIEW"]


def verdict(statuses):
    return next((s for s in PRIORITY if s in statuses), "PASS")


def apply(ctx):
    keys = {(r["batch"], r["analyte"]) for r in ctx["effective"]}
    out = []
    for key in sorted(keys):
        rows = [r for source in [ctx["parallel"], ctx["recoveries"], ctx["blank_checks"]]
                for r in source if (r["batch"], r["analyte"]) == key]
        statuses = [r["status"] for r in rows]
        if not any((r["batch"], r["analyte"]) == key for r in ctx["blank_checks"]):
            statuses.append("BLANK_MISSING")
        status = verdict(statuses)

        # 证据谱系：该检测批下每条结论共享哪份测量，哪些另有独立证据
        local = [c for c in ctx.get("conclusions", [])
                 if (c["batch"], c["analyte"]) == key]
        group_ids = sorted({c["evidence_group"] for c in local})
        shared_groups = sorted({c["evidence_group"] for c in local if c["shared_evidence"]})
        independent_groups = sorted({c["evidence_group"] for c in local if not c["shared_evidence"]})
        shared_lines = sorted({m["line"] for c in local if c["shared_evidence"]
                               for m in c["measurements"]})
        independent_lines = sorted({m["line"] for c in local if not c["shared_evidence"]
                                    for m in c["measurements"]})

        out.append({
            "batch": key[0], "analyte": key[1], "status": status,
            "checks": len(rows), "failed": sum(s != "PASS" for s in statuses),
            "结论": [{"family": c["family"], "pair": c["pair"], "status": c["status"],
                    "evidence_group": c["evidence_group"],
                    "shared_evidence": c["shared_evidence"],
                    "measurement_lines": [m["line"] for m in c["measurements"]]}
                   for c in local],
            "证据组": group_ids,
            "共享证据组": shared_groups,
            "独立证据组": independent_groups,
            "共享测量行": shared_lines,
            "独立测量行": independent_lines,
        })
    ctx["released"] = out
    ctx["blocked"] = not out or any(r["status"] != "PASS" for r in out)
    ctx["balance"] = {"input": ctx["input_count"],
                      "accepted": ctx["input_count"] - len(ctx["quarantine"]) - ctx["blank_rows"],
                      "quarantined": len(ctx["quarantine"]), "blank": ctx["blank_rows"]}
    summary = dict(可放行=sum(r["status"] == "PASS" for r in out),
                   阻断=sum(r["status"] != "PASS" for r in out))
    summary.update(ctx.get("evidence_summary", {}))
    return report(out, **summary)
