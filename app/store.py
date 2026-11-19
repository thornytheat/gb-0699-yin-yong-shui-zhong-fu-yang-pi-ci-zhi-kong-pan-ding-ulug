import sqlite3
import json
import hashlib
from datetime import datetime, timezone
from app.config import DATA_DIR, RULE_VERSION
from app.errors import BusinessError

# runs：批次当前指针（单行，随新版本原子切换）
# run_versions：不可变版本流水，只追加；任何更新失败都保留全部旧版，杜绝数据丢失
_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    current_version INTEGER NOT NULL DEFAULT 1,
    review_revision INTEGER NOT NULL DEFAULT 0,
    decision TEXT NOT NULL DEFAULT '待复核',
    digest TEXT NOT NULL,
    updated TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS run_versions (
    run_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    parent_version INTEGER NOT NULL,
    digest TEXT NOT NULL,
    extra_digest TEXT NOT NULL DEFAULT '',
    source_text TEXT NOT NULL,
    result TEXT NOT NULL,
    affected TEXT NOT NULL,
    created TEXT NOT NULL,
    PRIMARY KEY (run_id, version)
);
"""


def connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DATA_DIR / "runs.sqlite", timeout=15)
    db.row_factory = sqlite3.Row
    _migrate(db)
    db.executescript(_SCHEMA)
    _ensure_columns(db)
    return db


def _ensure_columns(db):
    """对已存在的新结构表补列，已存在则跳过；不触碰任何数据行。"""
    cols = {r[1] for r in db.execute("PRAGMA table_info(run_versions)")}
    if "extra_digest" not in cols:
        db.execute("ALTER TABLE run_versions ADD COLUMN extra_digest TEXT NOT NULL DEFAULT ''")
        db.commit()


def _migrate(db):
    """旧版单行 runs 表无损迁移为 指针表+不可变版本表；迁移失败整体回滚。"""
    cols = {r[1] for r in db.execute("PRAGMA table_info(runs)")}
    if not cols or "current_version" in cols:
        return  # 已是新结构
    legacy = db.execute("SELECT id,digest,result,revision,decision,created FROM runs").fetchall()
    db.execute("ALTER TABLE runs RENAME TO runs_legacy")
    db.executescript(_SCHEMA)
    now = datetime.now(timezone.utc).isoformat()
    for r in legacy:
        db.execute("INSERT INTO runs(id,current_version,review_revision,decision,digest,updated) "
                   "VALUES(?,1,?,?,?,?)",
                   (r["id"], r["revision"], r["decision"], r["digest"], now))
        db.execute("INSERT INTO run_versions(run_id,version,parent_version,digest,source_text,"
                   "result,affected,created) VALUES(?,1,1,?,'',?, '[]',?)",
                   (r["id"], r["digest"], r["result"], r["created"]))
    db.execute("DROP TABLE runs_legacy")
    db.commit()


def _digest(text):
    return hashlib.sha256((RULE_VERSION + "\n" + text).encode()).hexdigest()


def _row_to_item(row, vrow):
    result = json.loads(vrow["result"])
    return {
        "id": row["id"],
        "digest": row["digest"],
        "result": result,
        "rule_version": result.get("rule_version", "2026.11.18.1"),
        "revision": row["review_revision"],
        "data_version": row["current_version"],
        "decision": row["decision"],
        "created": vrow["created"],
        "updated": row["updated"],
        "affected": json.loads(vrow["affected"]),
    }


def _fetch(db, ident):
    row = db.execute("SELECT * FROM runs WHERE id=?", (ident,)).fetchone()
    if row is None:
        raise BusinessError("NOT_FOUND", "批次不存在", 404)
    vrow = db.execute("SELECT * FROM run_versions WHERE run_id=? AND version=?",
                      (ident, row["current_version"])).fetchone()
    return row, vrow


def _first_version_id(digest):
    # 首个版本沿用摘要前16位，保持与历史批次 id 形状一致；派生版本另起派生 id
    return digest[:16]


def save(text, result):
    """同规则版本、同输入摘要只产生一条批次：重复运行直接返回既有记录，不新增。"""
    digest = _digest(text)
    ident = _first_version_id(digest)
    now = datetime.now(timezone.utc).isoformat()
    payload = json.dumps(dict(result, rule_version=RULE_VERSION), ensure_ascii=False)
    with connect() as db:
        existing = db.execute("SELECT run_id AS id FROM run_versions WHERE digest=?",
                              (digest,)).fetchone()
        if existing:
            row, vrow = _fetch(db, existing["id"])
            return _row_to_item(row, vrow)
        # 新批次：指针与首版本同事务写入，任一失败整体回滚
        db.execute("INSERT INTO runs(id,current_version,review_revision,decision,digest,updated) "
                   "VALUES(?,1,0,'待复核',?,?)", (ident, digest, now))
        db.execute("INSERT INTO run_versions(run_id,version,parent_version,digest,"
                   "extra_digest,source_text,result,affected,created) "
                   "VALUES(?,1,1,?,'',?,?, '[]',?)",
                   (ident, digest, text, payload, now))
        row, vrow = _fetch(db, ident)
        return _row_to_item(row, vrow)


def get(ident):
    with connect() as db:
        row, vrow = _fetch(db, ident)
        return _row_to_item(row, vrow)


def history():
    with connect() as db:
        return [dict(r) for r in db.execute(
            "SELECT id,current_version AS data_version,review_revision AS revision,"
            "decision,updated AS created FROM runs ORDER BY updated DESC LIMIT 40")]


def versions(ident):
    """返回批次的全部不可变版本（含每版受影响结论），供审计与回滚核对。"""
    with connect() as db:
        if db.execute("SELECT 1 FROM runs WHERE id=?", (ident,)).fetchone() is None:
            raise BusinessError("NOT_FOUND", "批次不存在", 404)
        return [{"version": r["version"], "parent_version": r["parent_version"],
                 "digest": r["digest"],
                 "kind": "supplement" if r["extra_digest"] else "initial",
                 "affected": json.loads(r["affected"]),
                 "created": r["created"]}
                for r in db.execute("SELECT version,parent_version,digest,extra_digest,affected,created "
                                    "FROM run_versions WHERE run_id=? ORDER BY version", (ident,))]


def _diff_conclusions(old_result, new_result):
    """只标记放行结论发生变化的检测批；未受影响的结论保持沿用。"""
    def snap(result):
        return {(r["batch"], r["analyte"]):
                (r["status"], r["checks"], r["failed"], r["共享测量行"], r["独立测量行"])
                for r in result.get("released", [])}
    old, new = snap(old_result), snap(new_result)
    return sorted([{"batch": k[0], "analyte": k[1], "before": old.get(k), "after": new[k]}
                   for k in set(old) | set(new) if old.get(k) != new.get(k)],
                  key=lambda x: (x["batch"], x["analyte"]))


def supplement(ident, expected_version, extra_text, new_text, new_result):
    """补入独立样：仅当调用方已在事务外完成计算后调用；本函数整体原子提交。

    - expected_version 乐观锁：期间他人已更新则 409，调用方拿到的仍是旧版
    - 先写新版本再切指针，任何异常回滚，旧版本与旧指针原样保留
    - 同一补充内容重复提交按补充内容摘要幂等，不产生新版本
    """
    digest = _digest(new_text)
    extra_digest = _digest(extra_text)  # 幂等键锚定补充内容本身，而非合并后的全文
    now = datetime.now(timezone.utc).isoformat()
    payload = json.dumps(dict(new_result, rule_version=RULE_VERSION), ensure_ascii=False)
    with connect() as db:
        row, vrow = _fetch(db, ident)
        if row["current_version"] != expected_version:
            raise BusinessError("STALE", "批次已有新版本，请刷新后重试", 409)
        # 重跑同一批补充：按补充内容摘要命中既有版本，直接返回当前记录，不新增
        if db.execute("SELECT 1 FROM run_versions WHERE run_id=? AND extra_digest=?",
                      (ident, extra_digest)).fetchone():
            return _row_to_item(*_fetch(db, ident))
        old_result = json.loads(vrow["result"])
        affected = _diff_conclusions(old_result, new_result)
        next_version = row["current_version"] + 1
        # 补样产生新数据版本：复核流水中止，决定回到待复核；review_revision 不回退以保留审计轨迹
        db.execute("INSERT INTO run_versions(run_id,version,parent_version,digest,extra_digest,"
                   "source_text,result,affected,created) VALUES(?,?,?,?,?,?,?,?,?)",
                   (ident, next_version, row["current_version"], digest, extra_digest,
                    new_text, payload, json.dumps(affected, ensure_ascii=False), now))
        switched = db.execute(
            "UPDATE runs SET current_version=?, digest=?, decision='待复核', updated=? "
            "WHERE id=? AND current_version=?",
            (next_version, digest, now, ident, expected_version)).rowcount
        if not switched:  # 并发下版本已被推进：整笔回滚，旧版保留
            raise BusinessError("STALE", "批次已有新版本，请刷新后重试", 409)
        item = _row_to_item(*_fetch(db, ident))
        item["affected"] = affected
        return item


def review(ident, revision, decision):
    if not isinstance(decision, str) or decision not in {"通过", "退回"}:
        raise BusinessError("DECISION", "复核决定无效")
    with connect() as db:
        row, vrow = _fetch(db, ident)  # 复用同一连接，避免写事务内二次连接自锁
        current = _row_to_item(row, vrow)
        if decision == "通过" and current["result"].get("blocked"):
            raise BusinessError("BLOCKED", "存在阻断项，请先修正数据", 409)
        changed = db.execute(
            "UPDATE runs SET review_revision=review_revision+1, decision=? "
            "WHERE id=? AND review_revision=?",
            (decision, ident, revision)).rowcount
        if not changed:
            raise BusinessError("STALE", "版本已更新，请刷新", 409)
        return _row_to_item(*_fetch(db, ident))
