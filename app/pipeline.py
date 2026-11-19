from pathlib import Path
from app.report import plain,reason_counts
from app.modules.m1_samples.rules import apply as stage1
from app.modules.m2_contract.rules import apply as stage2
from app.modules.m3_parallel.rules import apply as stage3
from app.modules.m4_spikes.rules import apply as stage4
from app.modules.m5_blanks.rules import apply as stage5
from app.modules.m6_release.rules import apply as stage6
from app.modules.m7_retest.rules import apply as stage7

def sample_text():
    return (Path(__file__).parent.parent/"sample_data"/"instrument.csv").read_text(encoding="utf-8-sig")

def run(text):
    ctx={"text":text,"quarantine":[],"reports":[]}
    ctx["reports"].append(stage1(ctx))
    ctx["reports"].append(stage2(ctx))
    ctx["reports"].append(stage3(ctx))
    ctx["reports"].append(stage4(ctx))
    ctx["reports"].append(stage5(ctx))
    ctx["reports"].append(stage6(ctx))
    ctx["reports"].append(stage7(ctx))
    ctx.pop("text",None)
    ctx["reasons"]=reason_counts(ctx)
    return plain(ctx)
