# KPL二路说 · 二路解说观点聚合

个人独立开发的 KPL 粉丝站，**非官方产品**。上线：https://erlushuo.xyz

## 问题

看完一场 KPL 比赛，观众最想知道的是「专业的人怎么评价这场」——而 B站的「二路解说」（陪看解说）视频正是最直接的答案。但每场比赛同时有十几家二路在解说，一个观众不可能全部看完，大量有价值的观点因此被埋没。

## 解法

用 AI 把这十几个人的解说音频全部听完，按比赛整理成几分钟能看完的结构化赛评：BP 点评、选手评价、赛后复盘、金句时刻，原话引用可一键跳转回原视频对应时间点。

## 产品决策

这个项目最初的构想是更宽泛的「KPL 玩梗社区」（自动生成梗图/热点话题），试运行后判断**功能求多不如求准**——玩梗内容同质化严重、留存弱，而「这场比赛专业人士怎么评价」是一个更窄但更真实的高频需求，于是砍掉玩梗方向、把资源全部收拢到二路观点聚合这一件事上。

几个跟着这个判断走的具体取舍：

- **覆盖优先于精选**：一度限制每场比赛只处理 3-6 位头部解说以控制转写成本，后改为不设上限、覆盖合集视频里出现的所有解说——观众要看的是"这场比赛全网怎么评"，人为砍掉长尾解说等于砍掉了产品的核心承诺
- **说话人分离而非整段转写**：解说音频里混有背景的官方直播解说声，必须先分离出目标解说本人的声纹，再单独转写，否则观点会被官方解说的内容污染
- **AI 结论一律标注 + 原话可溯源**：不伪造真实感，所有 AI 提取的内容标「AI 生成」，原话引用附时间戳跳转原视频，观众可以自行核实 AI 有没有曲解
- **赛程与观点合一，不做重复列表**：早期首页单独维护一份"已出观点的比赛"列表，和赛程页信息重叠、造成用户要在两个页面来回找同一场比赛，后合并成一张赛程表，每行直接带出该场的解说观点数与名单

## 现状

- 覆盖当前赛季 88 场完赛（共 90 场）
- 已产出观点视频 36 个，正在追赶全量转写模式下的历史积压
- 服务器 7×24 小时自动运行：B站新投稿出现 → 匹配赛程 → 下载音频 → 转写 → 分析 → 上线，全链路无需人工介入

## 怎么做的（技术概览）

```
B站二路解说合集视频
   │  官方赛程 API 做视频↔比赛匹配
   ▼
FunASR（paraformer-zh + cam++）转写 + 说话人分离
   │  只保留解说人声，过滤背景官方解说
   ▼
DeepSeek 结构化观点提取 + 终审
   │  逐局分析 → 系列赛汇总 → 原话回转写做子串校验
   ▼
Supabase（Postgres + RLS）
   ▼
Next.js（Vercel）赛程 + 比赛详情页
```

- **pipeline/**（Python）：B站/官方赛事适配器、FunASR 转写、DeepSeek 观点提取、`scripts.watcher` 云端常驻监听
- **web/**（Next.js App Router）：赛程列表、比赛详情、选手页
- **supabase/migrations/**：`0001` 赛程基础表，`0002` 二路观点聚合表 + RLS

## 快速开始

### pipeline（本地）

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

服务器常驻走 `systemd`（见 `scripts/watcher.py` 顶部注释），`ASR_DEVICE` 环境变量可切 `cuda:0` 走 GPU。

### web

```powershell
cd web
npm install
npm run dev
```

生产部署为**手动 `vercel --prod`**，push 到 GitHub 不会自动触发部署。

### Supabase

1. 新建 Supabase 项目，依次执行 `supabase/migrations/0001_init.sql`、`0002_er_lu_insights.sql`
2. 把 URL / anon / service_role 写入 `pipeline/.env` 与 `web/.env.local`（参考 `.env.example`）

## 合规

- 页脚「非官方 / AI 生成标识 / 举报邮箱」
- 零选手照片、零官方海报
- AI 内容 100% 标识 + `ai_generations` 审计留痕
- 观点引用归属原 UP 主，附原视频跳转链接；解说本人可要求下架
