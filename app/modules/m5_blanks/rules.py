from app.report import report
from app.modules.m2_contract.rules import LIMITS


def _key(r):
    return (r["batch"], r["analyte"], r["id"], r["rev"], r["line"])


def blank_check(value, mdl, censored=False):
    if censored:
        return "PASS" if value <= mdl else "CENSORED_REVIEW"
    return "BLANK_FAIL" if value > mdl else "PASS"


def apply(ctx):
    out = []
    for r in ctx["effective"]:
        if r["kind"] != "blank":
            continue
        out.append(dict(id=r["id"], batch=r["batch"], analyte=r["analyte"],
                        value_mg=r["value_mg"], mdl=LIMITS[r["analyte"]],
                        status=blank_check(r["value_mg"], LIMITS[r["analyte"]], r["censored"]),
                        line=r["line"], measurements=(_key(r),)))
    ctx["blank_checks"] = out
    return report(out, 空白样=len(out), 污染=sum(r["status"] == "BLANK_FAIL" for r in out))
