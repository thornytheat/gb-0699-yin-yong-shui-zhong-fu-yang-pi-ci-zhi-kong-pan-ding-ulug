from decimal import Decimal
from app.numbers import number
from app.report import report,quarantine
from app.errors import BusinessError
UNITS={"mg/L":Decimal(1),"ug/L":Decimal("0.001")}
LIMITS={"Pb":Decimal("0.001"),"As":Decimal("0.001")}
def measure(text,unit):
    if unit not in UNITS:raise BusinessError("UNIT","浓度单位无效")
    censored=str(text).startswith("<");value=number(str(text)[1:] if censored else text)*UNITS[unit]
    if value<0:raise BusinessError("NEGATIVE","浓度不能为负")
    return value,censored

def latest(rows):
    chosen={}
    for r in rows:
        key=(r["batch"],r["analyte"],r["id"])
        if key not in chosen or r["rev"]>chosen[key]["rev"]:chosen[key]=r
    return list(chosen.values())

def apply(ctx):
    out=[]
    for r in ctx["raw"]:
        try:
            if r["analyte"] not in LIMITS:raise BusinessError("ANALYTE","检测项无效")
            if r["kind"] not in {"sample","duplicate","spike","blank"}:raise BusinessError("KIND","样品类别无效")
            x=dict(r);x["value_mg"],x["censored"]=measure(r["value"],r["unit"]);x["spike_mg"],_=measure(r["spike"],r["unit"]);x["rev"]=int(r["version"])
            if x["rev"]<1:raise BusinessError("VERSION","版本须大于零")
            out.append(x)
        except (BusinessError,ValueError) as e:quarantine(ctx,r,getattr(e,"code","VERSION"))
    ctx["normalized"]=out;ctx["effective"]=latest(out)
    return report(ctx["effective"],有效=len(ctx["effective"]),历史=len(out)-len(ctx["effective"]),单位="mg/L")
