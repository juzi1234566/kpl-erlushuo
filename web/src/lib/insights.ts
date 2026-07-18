import { getSupabase } from "./supabase";

export type DbMatch = {
  id: string;
  team1_id: string | null;
  team2_id: string | null;
  score1: number | null;
  score2: number | null;
  bo: number | null;
  status: number | null;
  start_time: string | null;
  stage_name: string | null;
  stage_desc: string | null;
};

export type DbTeam = {
  id: string;
  name: string;
  abbreviation: string | null;
};

export type DbVodSource = {
  id: string;
  bvid: string;
  title: string | null;
  up_name: string | null;
  caster_name: string | null;
  page_start: number | null;
  pubdate: string | null;
  duration_s: number | null;
};

export type InsightQuote = {
  text: string;
  start_ms: number;
  verdict?: string; // 预测：应验 / 打脸 / 未验证
  note?: string;
  context?: string;
};

export type InsightExtra = {
  headline?: string;
  verdict?: string;
  points?: string[];
  predictions?: InsightQuote[];
  turning_points?: { desc: string; quote?: InsightQuote | null }[];
  highlight?: string;
  lowlight?: string;
  main?: { name: string; reason: string }[];
};

export type DbCommentaryInsight = {
  id: string;
  vod_id: string;
  match_id: string;
  subject_type: "overall" | "team" | "player" | "bp" | "flow" | "blame" | "golden";
  subject_name: string;
  sentiment: "好评" | "差评" | "中立" | "复杂";
  rating: number | null;
  summary: string;
  quotes: InsightQuote[] | null;
  extra: InsightExtra | null;
};

export type MatchInsights = {
  match: DbMatch | null;
  teams: Record<string, DbTeam>;
  vods: DbVodSource[];
  insightsByVod: Record<string, DbCommentaryInsight[]>;
};

/** 本地开发回退：读 pipeline/data/insights/*.json（分析脚本产物），无需云端表 */
async function fetchLocalInsights(matchId: string): Promise<Pick<MatchInsights, "vods" | "insightsByVod">> {
  const empty = { vods: [] as DbVodSource[], insightsByVod: {} as Record<string, DbCommentaryInsight[]> };
  try {
    const { readdir, readFile } = await import("fs/promises");
    const path = await import("path");
    const dir = path.join(process.cwd(), "..", "pipeline", "data", "insights");
    const files = (await readdir(dir)).filter((f) => f.endsWith(".json"));
    const vods: DbVodSource[] = [];
    const insightsByVod: Record<string, DbCommentaryInsight[]> = {};
    for (const f of files) {
      const d = JSON.parse(await readFile(path.join(dir, f), "utf-8"));
      if (String(d.match_id) !== String(matchId)) continue;
      const vodId = `local-${f}`;
      vods.push({
        id: vodId,
        bvid: d.bvid,
        title: `${d.caster} 二路解说`,
        up_name: d.caster,
        caster_name: d.caster,
        page_start: Array.isArray(d.pages) ? d.pages[0] : 1,
        pubdate: null,
        duration_s: null,
      });
      const rows: DbCommentaryInsight[] = [];
      const push = (
        subject_type: DbCommentaryInsight["subject_type"],
        subject_name: string,
        item: {
          sentiment?: string;
          rating?: number;
          summary?: string;
          quotes?: InsightQuote[];
        } | null,
        extra: InsightExtra = {},
      ) => {
        if (!item?.summary) return;
        rows.push({
          id: `${vodId}-${subject_type}-${subject_name}`,
          vod_id: vodId,
          match_id: String(matchId),
          subject_type,
          subject_name,
          sentiment: (item.sentiment as DbCommentaryInsight["sentiment"]) || "中立",
          rating: item.rating ?? null,
          summary: item.summary,
          quotes: item.quotes || [],
          extra,
        });
      };
      // headline/verdict/points 落 extra；summary 仅作兜底文本
      const summarize = (item: {
        headline?: string;
        verdict?: string;
        summary?: string;
        points?: string[];
      }) => item?.headline || item?.verdict || item?.summary || (item?.points || [])[0] || "";
      if (d.bp)
        push("bp", "BP与阵容", { ...d.bp, summary: summarize(d.bp) }, {
          headline: d.bp.headline,
          points: d.bp.points || [],
          predictions: d.bp.predictions || [],
        });
      if (d.flow) {
        const flowSummary = [
          d.flow.early && `【前期】${d.flow.early}`,
          d.flow.mid && `【中期】${d.flow.mid}`,
          d.flow.late && `【后期】${d.flow.late}`,
        ]
          .filter(Boolean)
          .join("\n");
        push("flow", "局势走向", { ...d.flow, summary: flowSummary }, {
          turning_points: d.flow.turning_points || [],
        });
      }
      if (d.overall)
        push("overall", "整场比赛", { ...d.overall, summary: summarize(d.overall) }, {
          headline: d.overall.headline,
          points: d.overall.points || [],
        });
      for (const t of d.teams || [])
        push("team", t.name, { ...t, summary: summarize(t) }, {
          verdict: t.verdict,
          points: t.points || [],
        });
      for (const p of d.players || [])
        push("player", p.name, { ...p, summary: summarize(p) }, {
          verdict: p.verdict,
          points: p.points || [],
          highlight: p.highlight,
          lowlight: p.lowlight,
        });
      if (d.blame)
        push("blame", "赛后分锅", { ...d.blame, summary: summarize(d.blame) }, {
          headline: d.blame.headline,
          main: d.blame.main || [],
        });
      if (d.golden_quotes?.length)
        push("golden", "金句时刻", {
          summary: "本场解说金句",
          sentiment: "中立",
          quotes: d.golden_quotes,
        });
      insightsByVod[vodId] = rows;
    }
    return { vods, insightsByVod };
  } catch {
    return empty;
  }
}

/** 比赛详情 + 二路观点（云端优先，本地 JSON 回退） */
export async function fetchMatchInsights(matchId: string): Promise<MatchInsights> {
  const empty: MatchInsights = { match: null, teams: {}, vods: [], insightsByVod: {} };
  const sb = getSupabase();
  if (!sb) return empty;

  try {
    const { data: match } = await sb
      .from("matches")
      .select("id,team1_id,team2_id,score1,score2,bo,status,start_time,stage_name,stage_desc")
      .eq("id", matchId)
      .maybeSingle();
    if (!match) return empty;

    const teamIds = [match.team1_id, match.team2_id].filter(Boolean) as string[];
    const { data: teamRows } = await sb
      .from("teams")
      .select("id,name,abbreviation")
      .in("id", teamIds);
    const teams: Record<string, DbTeam> = {};
    for (const t of teamRows || []) teams[t.id] = t;

    const { data: insights, error } = await sb
      .from("commentary_insights")
      .select("id,vod_id,match_id,subject_type,subject_name,sentiment,rating,summary,quotes")
      .eq("match_id", matchId)
      .eq("status", "approved");

    // 云端表不存在或无数据 → 本地 JSON 回退（开发模式）
    if (error || !insights?.length) {
      const local = await fetchLocalInsights(matchId);
      return { match: match as DbMatch, teams, ...local };
    }

    const vodIds = [...new Set(insights.map((i) => i.vod_id))];
    let vods: DbVodSource[] = [];
    if (vodIds.length) {
      const { data: vodRows } = await sb
        .from("vod_sources")
        .select("id,bvid,title,up_name,caster_name,page_start,pubdate,duration_s")
        .in("id", vodIds);
      vods = vodRows || [];
    }

    const insightsByVod: Record<string, DbCommentaryInsight[]> = {};
    for (const i of insights) {
      (insightsByVod[i.vod_id] ||= []).push(i as DbCommentaryInsight);
    }

    return { match: match as DbMatch, teams, vods, insightsByVod };
  } catch {
    return empty;
  }
}

export function biliUrl(bvid: string, startMs?: number, page?: number | null): string {
  const t = startMs ? Math.max(0, Math.floor(startMs / 1000)) : 0;
  const params: string[] = [];
  if (page && page > 1) params.push(`p=${page}`);
  if (t) params.push(`t=${t}`);
  return `https://www.bilibili.com/video/${bvid}${params.length ? `?${params.join("&")}` : ""}`;
}

export function fmtTimestamp(ms: number): string {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${String(sec).padStart(2, "0")}`;
}
