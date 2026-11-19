# 共享测量不得被当成两次独立证明：M8 证据谱系
from app.pipeline import run, sample_text


def test_sample_base_measurement_is_shared(result):
    parallel = next(c for c in result["conclusions"]
                    if c["family"] == "PARALLEL" and c["pair"] == "P1")
    recovery = next(c for c in result["conclusions"]
                    if c["family"] == "RECOVERY" and c["pair"] == "P1")
    # 行2 的样底同时服务平行核对与加标回收：两条结论都带共享标记，且锚到同一测量行
    assert parallel["shared_evidence"] is True
    assert recovery["shared_evidence"] is True
    assert 2 in parallel["shared_lines"] and 2 in recovery["shared_lines"]


def test_blank_and_spike_are_independent(result):
    blank = next(c for c in result["conclusions"] if c["family"] == "BLANK")
    assert blank["shared_evidence"] is False
    assert blank["shared_lines"] == []


def test_evidence_summary_counts(result):
    # 10 个 pair 的样底被共享；平行样/加标/空白共 30 支为独立测量
    assert result["evidence_summary"]["共享测量数"] == 10
    assert result["evidence_summary"]["独立测量数"] == 30
    assert result["evidence_summary"]["结论数"] == 30


def test_release_row_lists_shared_and_independent_lines(result):
    b01 = next(r for r in result["released"] if r["batch"] == "B01")
    # 共享行只含 sample 行（2,6,10...），空白行 5/9/... 始终在独立侧
    assert set(b01["共享测量行"]).isdisjoint(b01["独立测量行"])
    assert 5 in b01["独立测量行"]
    assert b01["共享证据组"] and b01["独立证据组"]


def test_supplement_turns_recovery_into_independent_evidence(sample):
    extra = ("id,batch,analyte,kind,pair,value,spike,unit,version\n"
             "001X,B01,Pb,sample,P1,0.0031,0,mg/L,1\n")
    merged = sample.rstrip("\n") + "\n" + extra
    r = run(merged)
    rec = next(x for x in r["recoveries"] if x["pair"] == "P1")
    par = next(x for x in r["parallel"] if x["pair"] == "P1")
    assert rec["independent_base"] is True
    assert rec["base_line"] != par["measurements"][0][4]
    recovery = next(c for c in r["conclusions"]
                    if c["family"] == "RECOVERY" and c["pair"] == "P1")
    assert recovery["shared_evidence"] is False
    # 平行结论仍锚定原始登记的两支测量，补入的独立样不参与配对
    parallel = next(c for c in r["conclusions"]
                    if c["family"] == "PARALLEL" and c["pair"] == "P1")
    assert sorted(m["line"] for m in parallel["measurements"]) == [2, 3]


def test_extra_sample_does_not_break_pair(sample):
    extra = ("id,batch,analyte,kind,pair,value,spike,unit,version\n"
             "001X,B01,Pb,sample,P1,0.0031,0,mg/L,1\n")
    r = run(sample.rstrip("\n") + "\n" + extra)
    p1 = next(x for x in r["parallel"] if x["pair"] == "P1")
    assert p1["status"] != "PAIR_MISSING"
    assert len(r["parallel"]) == 10


def test_censored_independent_base_routes_to_review():
    text = ("id,batch,analyte,kind,pair,value,spike,unit,version\n"
            "001S,B09,Pb,sample,P1,0.003,0,mg/L,1\n"
            "001D,B09,Pb,duplicate,P1,0.0035,0,mg/L,1\n"
            "001A,B09,Pb,spike,P1,0.013,.01,mg/L,1\n"
            "001B,B09,Pb,blank,,.0002,0,mg/L,1\n"
            "001X,B09,Pb,sample,P1,<0.001,0,mg/L,1\n")
    r = run(text)
    rec = next(x for x in r["recoveries"] if x["pair"] == "P1")
    assert rec["independent_base"] is True
    assert rec["status"] == "CENSORED_REVIEW"
    par = next(x for x in r["parallel"] if x["pair"] == "P1")
    assert [m[4] for m in par["measurements"]] == [2, 3]


def test_evidence_counts_are_disjoint_and_complete():
    # 补入合格独立本底后：共享+独立测量数与结论引用的去重测量行总数自洽
    extra = ("id,batch,analyte,kind,pair,value,spike,unit,version\n"
             "001X,B01,Pb,sample,P1,0.0031,0,mg/L,1\n")
    r = run(sample_text().rstrip("\n") + "\n" + extra)
    referenced = {m["line"] for c in r["conclusions"] for m in c["measurements"]}
    assert r["evidence_summary"]["共享测量数"] + r["evidence_summary"]["独立测量数"] \
        == len(referenced)
