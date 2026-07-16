# Phase 0 验收（2026-07-16 起）

| 项 | 状态 | 备注 |
|----|------|------|
| 官方接口封装 | ✅ | `pipeline/sources/pvp_match_adapter.py` |
| 夏季赛 90 场赛程回填 | ✅ | `pipeline/data/raw/summary_20260003.json` |
| 对局详情 + 梗点信号 | ✅ | `scripts/spike_battle.py` |
| hero_id 映射 | ✅ | 当前 53 个英雄（随回填增长） |
| mock + 真生梗 | ✅ | DeepSeek 已接入，样例：「橘右京教你做人…」 |
| Supabase SQL | ✅ | `0001_init.sql`；**密钥待填入本机 .env** |
| Next.js 骨架 + 梗百科 + OG | ✅ | 已接 Supabase 读库回落种子 |
| GitHub | ✅ | 私有仓 `juzi1234566/kpl-meme` |
| 同步脚本 | ✅ | `python -m scripts.sync_to_supabase` |
| yt-dlp 字幕 | ⏳ | 需浏览器 cookies |
| Vercel 部署 | ⏳ | 代码已推送，Root Directory=`web`，等 Supabase 环境变量 |

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
