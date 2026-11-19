# 补入独立样：在既有批次上追加独立测量，只重算受影响检测批的结论。
# 计算阶段不触碰数据库；全部成功后由 store.supplement 在单事务内提交，失败保留旧版。
from app.pipeline import run
from app.reader import read_rows
from app.modules.m1_samples.rules import FIELDS
from app import store
from app.errors import BusinessError


def merge_text(parent_text, extra_text):
    """合并父版本原文与补充 CSV；补充记录的物理行号在合并文件中自然顺延。"""
    parent = parent_text.rstrip("\n")
    extra_lines = extra_text.splitlines()
    if not extra_lines:
        raise BusinessError("SUPPLEMENT_EMPTY", "补充文件为空")
    extra_header = [h.strip() for h in extra_lines[0].split(",")]
    if set(extra_header) != set(FIELDS) or len(extra_header) != len(FIELDS):
        raise BusinessError("SUPPLEMENT_HEADER", "补充文件字段不匹配")
    body = "\n".join(extra_lines[1:]).strip()
    if not body:
        raise BusinessError("SUPPLEMENT_HEADER_ONLY", "补充文件只有表头")
    return parent + "\n" + body + "\n"


def supplement_run(ident, expected_version, extra_text):
    current = store.get(ident)
    # 1) 先在库外完成解析与全量重算：任何 422/结构错误都在写库前抛出，旧版原样保留
    merged = merge_text(_source_text(ident, current["data_version"]), extra_text)
    new_result = run(merged)
    # 2) 计算通过后原子提交版本；版本冲突或重复内容由 store 判定
    return store.supplement(ident, expected_version, extra_text, merged, new_result)


def _source_text(ident, version):
    from app.store import connect
    with connect() as db:
        row = db.execute("SELECT source_text FROM run_versions WHERE run_id=? AND version=?",
                         (ident, version)).fetchone()
    if row is None:
        raise BusinessError("NOT_FOUND", "批次版本不存在", 404)
    return row["source_text"]
