from app.report import report
PRIORITY=["BLANK_FAIL","BLANK_MISSING","RECOVERY_FAIL","SPIKE_ZERO","BASE_MISSING","PAIR_FAIL","PAIR_MISSING","CENSORED_REVIEW"]
def verdict(statuses):
    return next((s for s in PRIORITY if s in statuses),"PASS")

def apply(ctx):
    keys={(r["batch"],r["analyte"]) for r in ctx["effective"]};out=[]
    for key in sorted(keys):
        rows=[r for source in [ctx["parallel"],ctx["recoveries"],ctx["blank_checks"]] for r in source if (r["batch"],r["analyte"])==key]
        statuses=[r["status"] for r in rows]
        if not any((r["batch"],r["analyte"])==key for r in ctx["blank_checks"]):statuses.append("BLANK_MISSING")
        status=verdict(statuses);out.append({"batch":key[0],"analyte":key[1],"status":status,"checks":len(rows),"failed":sum(s!="PASS" for s in statuses)})
    ctx["released"]=out;ctx["blocked"]=not out or any(r["status"]!="PASS" for r in out)
    ctx["balance"]={"input":ctx["input_count"],"accepted":ctx["input_count"]-len(ctx["quarantine"])-ctx["blank_rows"],"quarantined":len(ctx["quarantine"]),"blank":ctx["blank_rows"]}
    return report(out,可放行=sum(r["status"]=="PASS" for r in out),阻断=sum(r["status"]!="PASS" for r in out))
