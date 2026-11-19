# 接口

`POST /api/run`：{"text":"CSV内容"}。同规则版本与输入摘要只产生一条批次。

`GET/POST /api/1` 至 `/api/8`：独立样例或自定义文件计算。各模块返回 report、quarantine、balance。M8 为证据谱系，按物理行号把每条质控结论锚定到具体测量。

`POST /api/runs/{id}/supplement`：{"data_version":整数,"text":"补充CSV"}。补入同 pair 的独立测量；库外完成校验与重算后单事务提交新版本，返回 affected（仅含放行结论变化的检测批）。同补充内容按摘要幂等，不新增版本；版本过期返回 409，结构错误 422 且旧版原样保留。

`GET /api/runs/{id}/versions`：批次的不可变版本链，含 parent_version、affected 与 initial/supplement 标记。

`POST /api/review`：id、整数revision（复核流水 review_revision）、decision取通过或退回。旧版本409；阻断项不能通过。补样产生新数据版本后决定重置为待复核，复核流水不回退。

`GET /api/export/{id}`：唯一证据CSV，含证据组（shared_evidence/independent_evidence）、放行结论、运行摘要与隔离记录。`GET /health`：存活检查。

错误：结构/数值422，版本冲突409，不存在404，文件过大413。逐行异常进入quarantine。

## 数据保证

- 共享证据：同一测量行同时充当平行样底与加标本底时，两条结论共享该测量，证据组标记 shared，不计为两次独立证明。
- 只重算受影响结论：补样后 affected 仅列状态/检查数/证据行变化的检测批，其余结论沿用。
- 无数据丢失：run_versions 只追加，先写新版本再原子切换 runs 指针；任何异常整体回滚。
- 幂等：同原文重跑 `/api/run` 返回同批次；同补充内容重跑 supplement 不新增版本。
