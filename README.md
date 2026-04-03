# 伊朗冲突监控

实时新闻监控仪表盘，追踪涉及伊朗的冲突相关事件。从多个 RSS 源和 NewsAPI 抓取新闻，按严重程度自动分类，存入 SQLite 数据库，并提供深色风格的 Web 仪表盘。

## 功能特性

- **多源 RSS 抓取** — 路透社、BBC、半岛电视台、AP、卫报、以色列时报、耶路撒冷邮报
- **NewsAPI 支持** — 配置 API Key 后可获取更多来源
- **相关性过滤** — 仅保留同时涉及"伊朗"与"冲突"关键词的事件
- **严重程度分类** — `极危 / 高危 / 中危 / 低危`，基于关键词规则自动判定
- **标签提取** — 核武器、导弹、无人机、制裁、外交、代理武装、伊斯兰革命卫队等
- **Telegram 推送** — 高危和极危事件可选配 Telegram 通知
- **Web 仪表盘** — 深色界面，支持筛选、搜索、实时统计，每分钟自动刷新，中英文一键切换
- **后台调度器** — 抓取间隔通过 `.env` 自由配置

## 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/szkangjian/iran-conflict-monitor.git
cd iran-conflict-monitor

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置（可选）
cp .env.example .env
# 编辑 .env，填写 NEWS_API_KEY、TELEGRAM_* 等

# 5. 运行
python main.py
# 仪表盘地址：http://localhost:5000
```

## 启动参数

```
python main.py              # 完整模式：抓取 + 调度器 + 仪表盘
python main.py --fetch-once # 单次抓取后退出，不启动仪表盘
python main.py --dashboard  # 仅启动仪表盘，不运行调度器
python main.py --port 8080  # 自定义端口
```

## 配置项

将 `.env.example` 复制为 `.env` 并按需修改：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `NEWS_API_KEY` | — | NewsAPI.org 密钥（可选） |
| `TELEGRAM_BOT_TOKEN` | — | Telegram 机器人 Token |
| `TELEGRAM_CHAT_ID` | — | Telegram 频道或用户 ID |
| `FETCH_INTERVAL_MINUTES` | `15` | 抓取间隔（分钟） |
| `DASHBOARD_PORT` | `5000` | 仪表盘端口 |
| `LOG_LEVEL` | `INFO` | 日志级别：`DEBUG / INFO / WARNING / ERROR` |

## 项目结构

```
iran_conflict_monitor/
├── config.py                  # 全局配置与关键词列表
├── main.py                    # 入口文件
├── requirements.txt
├── monitor/
│   ├── fetcher.py             # RSS + NewsAPI 抓取
│   ├── classifier.py          # 相关性过滤、严重程度、标签提取
│   ├── storage.py             # SQLite 数据层
│   └── alerts.py             # Telegram 推送
├── dashboard/
│   ├── app.py                 # Flask API（/api/events、/api/stats）
│   └── templates/index.html   # 单页仪表盘
├── data/                      # SQLite 数据库（已 gitignore）
├── logs/                      # 日志文件（已 gitignore）
└── tests/
    ├── test_classifier.py
    └── test_storage.py
```

## 运行测试

```bash
pip install pytest
pytest tests/ -v
```

## 添加新闻源

在 `config.py` 的 `RSS_FEEDS` 中添加任意 RSS 地址：

```python
RSS_FEEDS = [
    ...
    {"name": "我的源", "url": "https://example.com/rss"},
]
```

## 调整关键词

在 `config.py` 中修改 `IRAN_KEYWORDS`、`CONFLICT_KEYWORDS` 以及各严重程度的关键词列表，可以自定义相关性过滤和分级规则。
