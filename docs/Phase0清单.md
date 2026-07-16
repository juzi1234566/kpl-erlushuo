# Phase 0 验收（2026-07-16 起）

| 项 | 状态 | 备注 |
|----|------|------|
| 官方接口封装 | ✅ | `pipeline/sources/pvp_match_adapter.py` |
| 夏季赛 90 场赛程回填 | ✅ | `pipeline/data/raw/summary_20260003.json` |
| 对局详情 + 梗点信号 | ✅ | `scripts/spike_battle.py` |
| hero_id 映射 | ✅ | 当前 53 个英雄（随回填增长） |
| mock 生梗结构 | ✅ | 无 Key 时 mock；有 `DEEPSEEK_API_KEY` 走真模型 |
| Supabase SQL | ✅ | `supabase/migrations/0001_init.sql`（待你建项目执行） |
| Next.js 骨架 + 梗百科 + OG | ✅ | `web` 已 `npm run build` 通过 |
| DeepSeek 真模型 spike | ⏳ | 需你提供 API Key |
| yt-dlp 字幕 | ⏳ | 需浏览器 cookies |
| Vercel / 域名 / 云服务器 | ⏳ | 需账号与付款，未代购 |

## 本机命令

```powershell
# 管线
cd C:\Users\18413\Desktop\kpl-meme\pipeline
.\.venv\Scripts\Activate.ps1
python -m scripts.spike_api --leagues --matches
python -m scripts.backfill_league --league-id 20260003 --fetch-battles 5 --with-signals

# 网站
cd C:\Users\18413\Desktop\kpl-meme\web
npm run dev
```
