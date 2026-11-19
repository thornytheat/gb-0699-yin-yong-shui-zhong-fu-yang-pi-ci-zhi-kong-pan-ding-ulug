from decimal import Decimal
from app.report import report

def pair_check(a,b,mdl=Decimal("0.001"),censored=False):
    if censored:return {"status":"CENSORED_REVIEW","metric":None,"limit":None,"method":"限定值"}
    mean=(a+b)/2;diff=abs(a-b)
    if mean<5*mdl:return {"status":"PASS" if diff<=mdl else "PAIR_FAIL","metric":diff,"limit":mdl,"method":"绝对差mg/L"}
    relative=diff/mean
    return {"status":"PASS" if relative<=Decimal("0.20") else "PAIR_FAIL","metric":relative,"limit":Decimal("0.20"),"method":"相对偏差"}

def apply(ctx):
    groups={}
    for r in ctx["effective"]:
        if r["kind"] in {"sample","duplicate"}:groups.setdefault((r["batch"],r["analyte"],r["pair"]),[]).append(r)
    out=[]
    for key,rows in groups.items():
        left=[r for r in rows if r["kind"]=="sample"];right=[r for r in rows if r["kind"]=="duplicate"]
        if len(left)!=1 or len(right)!=1:out.append({"batch":key[0],"analyte":key[1],"pair":key[2],"status":"PAIR_MISSING","metric":None,"limit":None,"method":"配对"});continue
        check=pair_check(left[0]["value_mg"],right[0]["value_mg"],censored=left[0]["censored"] or right[0]["censored"])
        out.append(dict(batch=key[0],analyte=key[1],pair=key[2],left=left[0]["value_mg"],right=right[0]["value_mg"],**check))
    ctx["parallel"]=out;return report(out,配对=len(out),失败=sum(r["status"]!="PASS" for r in out))
