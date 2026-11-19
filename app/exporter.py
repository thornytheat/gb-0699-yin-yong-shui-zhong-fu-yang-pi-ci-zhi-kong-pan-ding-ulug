import csv
import io
import json


def evidence_csv(run):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["run_id", "sha256", "rule_version", "kind", "line", "reason", "evidence"])
    writer.writerow([run["id"], run["digest"], run["rule_version"], "manifest", "", "",
                     json.dumps({"balance": run["result"]["balance"], "decision": run["decision"],
                                 "revision": run["revision"], "data_version": run.get("data_version", 1),
                                 "evidence_summary": run["result"].get("evidence_summary", {})},
                                ensure_ascii=False)])
    # 证据谱系：每组测量服务于哪些质控结论，共享组显式标注，防止重复计为独立证明
    for g in run["result"].get("evidence_groups", []):
        writer.writerow([run["id"], run["digest"], run["rule_version"],
                         "shared_evidence" if g["shared"] else "independent_evidence",
                         "/".join(str(x) for x in g["measurement_lines"]),
                         ",".join(g["families"]), json.dumps(g, ensure_ascii=False)])
    for batch in run["result"].get("released", []):
        writer.writerow([run["id"], run["digest"], run["rule_version"], "release", "",
                         batch["status"], json.dumps(batch, ensure_ascii=False)])
    for row in run["result"].get("final", []):
        writer.writerow([run["id"], run["digest"], run["rule_version"], "result",
                         row.get("line", ""), row.get("status", ""), json.dumps(row, ensure_ascii=False)])
    for row in run["result"].get("quarantine", []):
        writer.writerow([run["id"], run["digest"], run["rule_version"], "quarantine",
                         row.get("line", ""), row["reason"], json.dumps(row, ensure_ascii=False)])
    return "﻿" + out.getvalue()
