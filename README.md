# 饮用水重复样与批次质控判定

水质监测数据复核员使用本工具归并采样平行样、加标样、空白样，对检测批给出放行结论。

## 核心计算

双样相对偏差分母零时单独判定；低浓度用绝对差阈值，高浓度用相对偏差；加标回收扣除本底。

## 启动

```bash
docker compose up --build -d
docker compose exec -T app pytest -q
docker compose config --quiet
```

浏览器访问 http://localhost:18213 。默认载入仓内样例。工具条可选择CSV文件运行；样例文件位于 `sample_data/instrument.csv`。重复执行同一内容复用同一批次。

## 模块

- M1 样品接收：`/module/1`，独立计算 `POST /api/1`。
- M2 检测项契约：`/module/2`，独立计算 `POST /api/2`。
- M3 平行样核对：`/module/3`，独立计算 `POST /api/3`。
- M4 加标回收：`/module/4`，独立计算 `POST /api/4`。
- M5 空白污染：`/module/5`，独立计算 `POST /api/5`。
- M6 批次放行：`/module/6`，独立计算 `POST /api/6`。
- M7 复测追踪：`/module/7`，独立计算 `POST /api/7`。

## 输入与输出

CSV可用UTF-8或GB18030；上传保留字符串编号和物理行号。POST `/api/run` 接收 `text` 字段。`GET /api/runs` 查询历史，`POST /api/review` 接收 id、revision、decision。导出按钮下载唯一证据CSV，含运行摘要与隔离记录。

SQLite命名卷保存运行记录。重建演示数据可更换卷名后重启。无需外部网络数据。规则定义见 `docs/DATA-DICTIONARY.md`；边界和测试对应关系见 `docs/DEPTH.md`。

## 范围

只处理仓内CSV定义，不连接生产系统。单次输入最多2MB。原始输入流式解析，业务计算阶段需容纳该文件的采信行。并非无限容量任务。
