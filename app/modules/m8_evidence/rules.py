# M8 证据谱系：把每条质控结论锚定到具体测量（按物理行号），
# 共享同一次测量的结论只生成一个证据组，避免被当成两次独立证明。
from app.report import report


def _group_id(measurements):
    """同一组测量集合生成稳定可读的证据组号：行号排序后拼接。"""
    lines = sorted(m["line"] for m in measurements)
    return "L" + "-".join(str(x) for x in lines)


def _measure_index(ctx):
    return {(r["batch"], r["analyte"], r["id"], r["rev"], r["line"]): r
            for r in ctx["effective"]}


def _measurement_refs(row, index):
    refs = []
    for key in row.get("measurements", ()):  # 由 M3/M4/M5 预先登记的测量键
        r = index.get(key)
        if r is not None:
            refs.append({"id": r["id"], "kind": r["kind"], "line": r["line"],
                         "batch": r["batch"], "analyte": r["analyte"],
                         "value_mg": r["value_mg"]})
    return refs


def build(ctx):
    """构建证据谱系并写入 ctx；M6 放行与 M8 报告共用同一份结果。"""
    index = _measure_index(ctx)
    sources = (
        ("PARALLEL", ctx.get("parallel", [])),
        ("RECOVERY", ctx.get("recoveries", [])),
        ("BLANK", ctx.get("blank_checks", [])),
    )
    groups = {}
    conclusions = []
    # 测量行 -> 引用它的质控家族；同一测量被多于一类结论引用即为共享证据
    line_families = {}
    for family, rows in sources:
        for row in rows:
            refs = _measurement_refs(row, index)
            gid = _group_id(refs) if refs else "L-"
            g = groups.setdefault(gid, {"group_id": gid, "families": set(),
                                        "measurement_lines": sorted(m["line"] for m in refs),
                                        "measurements": {}})
            g["families"].add(family)
            for m in refs:
                g["measurements"][m["line"]] = m
                line_families.setdefault(m["line"], set()).add(family)
            conclusions.append({
                "family": family,
                "batch": row["batch"],
                "analyte": row["analyte"],
                "pair": row.get("pair"),
                "status": row["status"],
                "evidence_group": gid,
                "measurement_count": len(refs),
                "measurements": refs,
            })

    shared_lines = {line for line, fams in line_families.items() if len(fams) > 1}
    independent_lines = set(line_families) - shared_lines

    for g in groups.values():
        # 证据组内只要含共享测量即标记：该组结论与其他结论共用了同一次测量
        g["shared"] = any(line in shared_lines for line in g["measurement_lines"])
        g["shared_lines"] = sorted(line for line in g["measurement_lines"] if line in shared_lines)
        g["families"] = sorted(g["families"])
        g["measurements"] = [g["measurements"][k] for k in sorted(g["measurements"])]

    for c in conclusions:
        c["shared_evidence"] = any(m["line"] in shared_lines for m in c["measurements"])
        c["shared_lines"] = sorted(m["line"] for m in c["measurements"] if m["line"] in shared_lines)

    ctx["evidence_groups"] = sorted(groups.values(), key=lambda g: g["group_id"])
    ctx["conclusions"] = conclusions
    ctx["evidence_summary"] = {
        "结论数": len(conclusions),
        "证据组": len(groups),
        "共享证据组": sum(1 for g in groups.values() if g["shared"]),
        "独立测量数": len(independent_lines),
        "共享测量数": len(shared_lines),
    }
    return ctx


def apply(ctx):
    build(ctx)
    return report(ctx["evidence_groups"], **ctx["evidence_summary"])
