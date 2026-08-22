# AI存量项目商机挖掘系统

基于《方案书.docx》构建的「采集→解析→匹配→推送→跟进」全链路自动化商机挖掘系统（狄耐克 · 老旧小区改造方向）。

## 目录结构

```
├── docs/              # 全流程开发文档（00-10）
├── sql/               # 数据库初始化脚本
├── backend/           # 后端服务（FastAPI）
│   └── app/
│       ├── api/       # 路由层
│       ├── models/    # ORM 模型
│       ├── schemas/   # Pydantic Schema
│       ├── services/  # 业务逻辑
│       ├── core/      # 配置/安全/数据库/日志
│       └── tasks/     # 异步任务
├── collector/         # 采集服务（Scrapy）
│   ├── spiders/       # 各数据源爬虫
│   ├── adapters/      # API 接入适配器
│   └── pipelines/     # 清洗/去重/入库
├── frontend/          # 前端（Vue3 + Vite + Element Plus + ECharts）
├── docker-compose.yml # 一键部署
└── .env.example       # 环境变量示例
```

## 快速开始

1. 复制 `.env.example` 为 `.env` 并配置环境变量（含 `DEEPSEEK_API_KEY`）。
2. 初始化数据库：执行 `sql/` 下脚本（或 `docker compose up -d` 后自动初始化）。
3. 启动后端：`cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload`。
4. 启动前端：`cd frontend && npm install && npm run dev`，访问 `http://localhost:5173`（默认账号 `admin/admin123`）。
5. 启动采集：`cd collector && python runner.py`。
6. 访问 API 文档：`http://localhost:8000/docs`。

详细说明见 `docs/` 目录文档。
