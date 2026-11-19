# 补入独立样：只重算受影响结论；更新失败保留旧版；重跑不新增记录
import pytest
from app.pipeline import run, sample_text
from app import store
from app.config import DATA_DIR
from app.supplement import supplement_run, merge_text
from app.errors import BusinessError

HEADER = "id,batch,analyte,kind,pair,value,spike,unit,version"


@pytest.fixture(autouse=True)
def _isolated_store():
    # 同样例在各用例间共享 run id，逐用例清空存储以保证隔离
    db = store.connect()
    db.execute("DELETE FROM run_versions")
    db.execute("DELETE FROM runs")
    db.commit()
    db.close()
    yield
    assert DATA_DIR.exists()


def _extra(pair="P1", sid="001X", value="0.0031"):
    return f"{HEADER}\n{sid},B01,Pb,sample,{pair},{value},0,mg/L,1\n"


@pytest.fixture
def saved():
    text = sample_text()
    return store.save(text, run(text))


def test_supplement_creates_new_version_keeps_old(saved):
    before = len(store.versions(saved["id"]))
    item = supplement_run(saved["id"], saved["data_version"], _extra())
    assert item["data_version"] == saved["data_version"] + 1
    versions = store.versions(saved["id"])
    assert len(versions) == before + 1
    assert versions[0]["kind"] == "initial" and versions[1]["kind"] == "supplement"
    # 旧版本仍可取回且内容未被覆盖
    assert versions[0]["digest"] != versions[1]["digest"]


def test_only_affected_conclusions_recomputed(saved):
    item = supplement_run(saved["id"], saved["data_version"], _extra())
    assert [(a["batch"], a["analyte"]) for a in item["affected"]] == [("B01", "Pb")]
    old_b02 = next(r for r in saved["result"]["released"] if r["batch"] == "B02")
    new_b02 = next(r for r in item["result"]["released"] if r["batch"] == "B02")
    assert (old_b02["status"], old_b02["checks"], old_b02["failed"]) == \
           (new_b02["status"], new_b02["checks"], new_b02["failed"])


def test_same_supplement_is_idempotent(saved):
    first = supplement_run(saved["id"], saved["data_version"], _extra())
    second = supplement_run(first["id"], first["data_version"], _extra())
    assert second["data_version"] == first["data_version"]
    assert len(store.versions(saved["id"])) == 2


def test_rerun_same_batch_adds_no_record(saved):
    again = store.save(sample_text(), run(sample_text()))
    assert again["id"] == saved["id"]
    assert again["data_version"] == saved["data_version"]


def test_stale_version_rejected_and_old_version_kept(saved):
    supplement_run(saved["id"], saved["data_version"], _extra())
    with pytest.raises(BusinessError, match="新版本"):
        supplement_run(saved["id"], 1, _extra(pair="P2", sid="002X"))
    assert store.get(saved["id"])["data_version"] == 2


def test_invalid_supplement_fails_before_persist(saved):
    with pytest.raises(BusinessError):
        supplement_run(saved["id"], saved["data_version"], "id,batch\nx,B01\n")
    current = store.get(saved["id"])
    assert current["data_version"] == saved["data_version"]
    assert len(store.versions(saved["id"])) == 1


def test_supplement_resets_decision_but_keeps_review_trail(saved):
    reviewed = store.review(saved["id"], saved["revision"], "退回")
    assert reviewed["revision"] == 1
    item = supplement_run(reviewed["id"], reviewed["data_version"], _extra())
    assert item["decision"] == "待复核"
    assert item["revision"] == 1  # 复核流水不回退
    assert item["data_version"] == 2


def test_merge_text_rejects_bad_header():
    with pytest.raises(BusinessError):
        merge_text(sample_text(), "id,batch\nx,1\n")


def test_versions_endpoint_shape(saved):
    supplement_run(saved["id"], saved["data_version"], _extra())
    versions = store.versions(saved["id"])
    assert {v["version"] for v in versions} == {1, 2}
    assert all("affected" in v and "digest" in v for v in versions)


def test_supplement_lines_continue_after_parent(saved):
    item = supplement_run(saved["id"], saved["data_version"], _extra())
    new_row = next(r for r in item["result"]["raw"] if r["id"] == "001X")
    # 父文件 46 行（含表头与尾空行），补充记录顺延到第 47 行，证据行号可追溯
    assert new_row["line"] == 47
    second = supplement_run(item["id"], item["data_version"],
                            _extra(pair="P2", sid="002X", value="0.0032"))
    assert next(r for r in second["result"]["raw"] if r["id"] == "002X")["line"] == 48


def test_supplement_api_happy_path_and_idempotence(saved):
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app, raise_server_exceptions=False)
    payload = {"data_version": saved["data_version"], "text": _extra()}
    resp = client.post(f"/api/runs/{saved['id']}/supplement", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_version"] == 2 and body["affected"]
    # 重放同一补充内容：带最新版本号时按补充摘要幂等，不新增版本
    replay = client.post(f"/api/runs/{saved['id']}/supplement",
                         json={"data_version": body["data_version"], "text": _extra()})
    assert replay.status_code == 200 and replay.json()["data_version"] == 2
    # 带旧版本号重放触发乐观锁，旧版保持不变
    stale = client.post(f"/api/runs/{saved['id']}/supplement", json=payload)
    assert stale.status_code == 409

    listed = client.get(f"/api/runs/{saved['id']}/versions").json()
    assert [v["version"] for v in listed["versions"]] == [1, 2]


def test_supplement_api_stale_and_bad_input(saved):
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app, raise_server_exceptions=False)
    supplement_run(saved["id"], saved["data_version"], _extra())
    stale = client.post(f"/api/runs/{saved['id']}/supplement",
                        json={"data_version": 1, "text": _extra(pair="P2", sid="002X")})
    assert stale.status_code == 409 and stale.json()["error"] == "STALE"
    bad = client.post(f"/api/runs/{saved['id']}/supplement",
                      json={"data_version": 2, "text": "id,batch\nx,1\n"})
    assert bad.status_code == 422
    assert store.get(saved["id"])["data_version"] == 2


def test_supplement_unknown_run_404():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/runs/nope/supplement",
                       json={"data_version": 1, "text": _extra()})
    assert resp.status_code == 404

