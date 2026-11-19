from decimal import Decimal
from app.report import report

def recovery(base,spiked,added):
    if added<=0:raise ValueError("加标量必须为正")
    return (spiked-base)/added*100

def apply(ctx):
    base={(r["batch"],r["analyte"],r["pair"]):r for r in ctx["effective"] if r["kind"]=="sample"};out=[]
    for r in ctx["effective"]:
        if r["kind"]!="spike":continue
        source=base.get((r["batch"],r["analyte"],r["pair"]))
        status="PASS";percent=None
        if not source:status="BASE_MISSING"
        elif source["censored"] or r["censored"]:status="CENSORED_REVIEW"
        else:
            try:
                percent=recovery(source["value_mg"],r["value_mg"],r["spike_mg"])
                if not Decimal(80)<=percent<=Decimal(120):status="RECOVERY_FAIL"
            except ValueError:status="SPIKE_ZERO"
        out.append({"id":r["id"],"batch":r["batch"],"analyte":r["analyte"],"pair":r["pair"],"recovery_pct":percent,"status":status,"line":r["line"]})
    ctx["recoveries"]=out;return report(out,加标样=len(out),失败=sum(r["status"]!="PASS" for r in out))
