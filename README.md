# 梗局 · KPL 粉丝玩梗社区（kpl-meme）

AI 驱动的 KPL 垂直玩梗社区（to C）。**非官方产品**。  
站内品牌：**梗局**；副标题可用「KPL 粉丝社区」——域名/商标请勿使用「KPL」本体。

> 基于计划：`KPL AI 玩梗社区 — 可行性调研与实施计划`  
> 目标锚点：2026-08-17 MVP 上线（季后赛流量 + 秋招作品双窗口）

## 战略约束（MVP）

1. **网站先行**，小程序延后到有工商主体后
2. AI 必须**明确标注身份**（禁止伪装真实用户暖场）
3. 数据主源：官方 `prod.comp.smoba.qq.com/leaguesite/*`（开放 JSON，需 Referer）

## 仓库结构

```
kpl-meme/
├── docs/                 # PRD、决策记录、合规声明草稿
├── supabase/migrations/  # Postgres schema + RLS
├── pipeline/             # 赛事同步 / AI worker（Python）
│   ├── sources/          # pvp 官方适配器
│   ├── signals/          # 规则梗点
│   ├── ai/               # 生梗 + 自评
│   └── scripts/          # 回填 / spike / 本地验收
└── web/                  # Next.js App Router（Vercel）
```

## 快速开始

### 1. 赛事管线（本地）

```powershell
cd C:\Users\18413\Desktop\kpl-meme\pipeline
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 列出赛季
python -m scripts.spike_api --leagues

# 同步 2026 夏季赛赛程到本地 JSON（不依赖 DB）
python -m scripts.backfill_league --league-id 20260003 --out data\raw

# 拉取一场对局详情 + 打印梗点信号
python -m scripts.spike_battle --battle-id 48251408_7_1781676660
```

### 2. Web

```powershell
cd C:\Users\18413\Desktop\kpl-meme\web
npm install
npm run dev
```

### 3. Supabase

1. 新建 Supabase 项目
2. 执行 `supabase/migrations/0001_init.sql`
3. 把 URL / anon / service_role 写入 `pipeline/.env` 与 `web/.env.local`

## 环境变量

见 `pipeline/.env.example`、`web/.env.example`。

## Phase 0 本周验收清单

- [x] 官方 4 类接口封装（leagues / matches / battles / battle）
- [x] 梗点信号规则引擎（横扫、极端 KDA、经济差等）
- [x] DB schema + RLS
- [x] Next.js 骨架 + 首页 / 梗百科占位 / OG 路由
- [ ] DeepSeek 生梗 prompt spike（需 API Key）
- [ ] yt-dlp 字幕 spike（需浏览器 cookies）
- [ ] Vercel 部署 + 域名 + Cloudflare
- [ ] 腾讯云轻量 + TMS 开通

## 合规提示

- 页脚必须「非官方 / AI 生成标识 / 举报邮箱」
- 零选手照片、零官方海报
- AI 内容 100% 标识 + `ai_generations` 审计留痕
