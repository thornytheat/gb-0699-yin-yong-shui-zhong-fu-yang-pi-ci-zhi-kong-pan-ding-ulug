from decimal import Decimal
from app.report import report


def _key(r):
    return (r["batch"], r["analyte"], r["id"], r["rev"], r["line"])


def recovery(base, spiked, added):
    if added <= 0:
        raise ValueError("加标量必须为正")
    return (spiked - base) / added * 100


def choose_base(samples, parallel_keys):
    """优先选未被平行样核对占用的独立测量；否则沿用共享本底（原行为）。

    返回 (本底行, 是否独立测量)。平行样占用键由 M3 的 measurements 提供，
    补入的独立样与原登记本底同属一个 pair，但有独立行号与编号。
    """
    independent = [r for r in samples if _key(r) not in parallel_keys]
    if independent:
        # 独立样多于一个时取最高版本、再取最大行号，保证结果确定可重放
        chosen = sorted(independent, key=lambda r: (r["rev"], r["line"]))[-1]
        return chosen, True
    if not samples:
        return None, False
    chosen = sorted(samples, key=lambda r: (r["rev"], r["line"]))[-1]
    return chosen, False


def apply(ctx):
    grouped = {}
    for r in ctx["effective"]:
        if r["kind"] == "sample":
            grouped.setdefault((r["batch"], r["analyte"], r["pair"]), []).append(r)
    parallel_keys = {k for row in ctx.get("parallel", []) for k in row.get("measurements", ())}
    out = []
    for r in ctx["effective"]:
        if r["kind"] != "spike":
            continue
        sources = grouped.get((r["batch"], r["analyte"], r["pair"]), [])
        source, independent = choose_base(sources, parallel_keys)
        status = "PASS"
        percent = None
        base_line = source["line"] if source else None
        if not source:
            status = "BASE_MISSING"
            measurements = (_key(r),)
        elif source["censored"] or r["censored"]:
            status = "CENSORED_REVIEW"
            measurements = (_key(source), _key(r))
        else:
            try:
                percent = recovery(source["value_mg"], r["value_mg"], r["spike_mg"])
                if not Decimal(80) <= percent <= Decimal(120):
                    status = "RECOVERY_FAIL"
            except ValueError:
                status = "SPIKE_ZERO"
            measurements = (_key(source), _key(r))
        out.append({"id": r["id"], "batch": r["batch"], "analyte": r["analyte"],
                    "pair": r["pair"], "recovery_pct": percent, "status": status,
                    "line": r["line"], "base_line": base_line,
                    "independent_base": bool(independent),
                    "measurements": measurements})
    ctx["recoveries"] = out
    return report(out, 加标样=len(out), 失败=sum(r["status"] != "PASS" for r in out),
                  独立本底=sum(1 for r in out if r["independent_base"]))
