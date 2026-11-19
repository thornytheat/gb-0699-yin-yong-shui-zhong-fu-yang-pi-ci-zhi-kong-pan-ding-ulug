from decimal import Decimal
from app.report import report


def _key(r):
    return (r["batch"], r["analyte"], r["id"], r["rev"], r["line"])


def pair_check(a, b, mdl=Decimal("0.001"), censored=False):
    if censored:
        return {"status": "CENSORED_REVIEW", "metric": None, "limit": None, "method": "限定值"}
    mean = (a + b) / 2
    diff = abs(a - b)
    if mean < 5 * mdl:
        return {"status": "PASS" if diff <= mdl else "PAIR_FAIL", "metric": diff, "limit": mdl, "method": "绝对差mg/L"}
    relative = diff / mean
    return {"status": "PASS" if relative <= Decimal("0.20") else "PAIR_FAIL",
            "metric": relative, "limit": Decimal("0.20"), "method": "相对偏差"}


def apply(ctx):
    groups = {}
    for r in ctx["effective"]:
        if r["kind"] in {"sample", "duplicate"}:
            groups.setdefault((r["batch"], r["analyte"], r["pair"]), []).append(r)
    out = []
    for key, rows in groups.items():
        left = sorted((r for r in rows if r["kind"] == "sample"),
                      key=lambda r: (r["line"], r["id"]))
        right = [r for r in rows if r["kind"] == "duplicate"]
        # 同 pair 补入的独立样不参与平行配对：平行成员固定为最早登记的那一支，
        # 额外测量（行号更大）交由 M4 作为独立加标本底，原配对结论保持可重算且不被冲掉
        if len(left) < 1 or len(right) != 1:
            out.append({"batch": key[0], "analyte": key[1], "pair": key[2],
                        "status": "PAIR_MISSING", "metric": None, "limit": None,
                        "method": "配对", "measurements": tuple(_key(r) for r in rows)})
            continue
        s, d = left[0], right[0]
        check = pair_check(s["value_mg"], d["value_mg"], censored=s["censored"] or d["censored"])
        out.append(dict(batch=key[0], analyte=key[1], pair=key[2],
                        left=s["value_mg"], right=d["value_mg"],
                        measurements=(_key(s), _key(d)), **check))
    ctx["parallel"] = out
    return report(out, 配对=len(out), 失败=sum(r["status"] != "PASS" for r in out))
