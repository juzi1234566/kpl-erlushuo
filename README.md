# KPL二路说 · 二路解说观点聚合（kpl-meme）

AI 自动聚合 B站「二路解说」视频观点的 KPL 粉丝站。**非官方产品**。

> 站点定位：KPL 二路解说视频太多看不完，AI 听完每一家的解说音频，
> 按比赛整理成「谁打得好、锅是谁的、预测有没有应验」的观点摘要，原话引用可跳转回原视频对应时间点。

线上地址：https://erlushuo.xyz （同 https://kpl-meme.vercel.app）

## 产品形态

1. 固定信任的 B站「二路解说」合集账号（如 up 主 `kpl二路`）作为视频来源
2. 服务器 7×24 小时轮询新投稿，标题匹配到已完赛场次后自动拉取音频
3. FunASR（paraformer-zh + cam++）转写 + 说话人分离，只保留解说人声，过滤掉背景官方解说
4. DeepSeek 提取「BP 点评 / 选手评价 / 赛后复盘 / 金句时刻」等结构化观点
5. 按比赛聚合展示，AI 生成内容全部标注身份，原话可跳转 B站原视频时间戳

## 仓库结构

```
kpl-meme/
├── docs/                    # PRD、决策记录
├── supabase/migrations/     # Postgres schema + RLS（0001 赛程/梗百科，0002 二路观点聚合）
├── pipeline/                # Python：赛事同步 / 转写 / AI 分析 / 云端监听
│   ├── sources/             # 官方赛事 API + B站 UP 主投稿适配器
│   ├── media/                # 音频下载（B站 API + CDN 直连）
│   ├── asr/                  # FunASR 转写 + 说话人归属
│   ├── ai/                    # DeepSeek 观点提取 / 终审 / 系列赛汇总
│   ├── signals/               # 视频 ↔ 比赛匹配
│   └── scripts/                # 各类入口脚本（见下）
└── web/                     # Next.js App Router（Vercel）
    └── src/app/              # 首页 / 赛程 / 比赛详情 / 选手页 / 关于
```

### pipeline 关键脚本

| 脚本 | 用途 |
|---|---|
| `scripts.watcher` | **服务器常驻**：轮询 UP 主新投稿，逐主播全链处理并增量上云，`systemd` 托管 |
| `scripts.analyze_collection` | 单个 (视频, 主播) 全链：下载→转写→说话人归属→逐局分析→系列赛汇总→终审 |
| `scripts.sync_to_supabase` | 官方赛程/战绩同步到 Supabase |
| `scripts.ingest_insights` / `aggregate_match` / `review_insights` | 观点入库 / 跨解说综合评 / 审核态刷新 |
| `scripts.scan_up_videos` | 手动扫描指定 UP 主投稿（`--dry-run` 核对匹配） |

## 快速开始

### 1. pipeline（本地）

```powershell
cd pipeline
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# torch 需先装 CPU 轮子，再装其余依赖
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# 单个视频全链验收
python -m scripts.analyze_collection --bvid BVxxxxx --pages 1-5 --caster 某解说 --match-id 2026071703
```

服务器部署走 `systemd`（见 `scripts/watcher.py` 顶部注释），`ASR_DEVICE` 环境变量可切 `cuda:0` 走 GPU。

### 2. web

```powershell
cd web
npm install
npm run dev
```

生产部署为**手动 `vercel --prod`**，push 到 GitHub 不会自动触发部署。

### 3. Supabase

1. 新建 Supabase 项目，依次执行 `supabase/migrations/0001_init.sql`、`0002_er_lu_insights.sql`
2. 把 URL / anon / service_role 写入 `pipeline/.env` 与 `web/.env.local`

## 环境变量

见 `pipeline/.env.example`、`web/.env.example`。

## 合规提示

- 页脚「非官方 / AI 生成标识 / 举报邮箱」
- 零选手照片、零官方海报
- AI 内容 100% 标识 + `ai_generations` 审计留痕
- 观点引用归属原 UP 主，附原视频跳转链接
