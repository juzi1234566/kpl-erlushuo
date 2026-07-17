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
  pubdate: string | null;
  duration_s: number | null;
};

export type InsightQuote = {
  text: string;
  start_ms: number;
};

export type DbCommentaryInsight = {
  id: string;
  vod_id: string;
  match_id: string;
  subject_type: "overall" | "team" | "player";
  subject_name: string;
  sentiment: "好评" | "差评" | "中立" | "复杂";
  rating: number | null;
  summary: string;
  quotes: InsightQuote[] | null;
};

export type MatchInsights = {
  match: DbMatch | null;
  teams: Record<string, DbTeam>;
  vods: DbVodSource[];
  insightsByVod: Record<string, DbCommentaryInsight[]>;
};

/** 比赛详情 + 二路观点（只取审核通过的） */
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

    const { data: insights } = await sb
      .from("commentary_insights")
      .select("id,vod_id,match_id,subject_type,subject_name,sentiment,rating,summary,quotes")
      .eq("match_id", matchId)
      .eq("status", "approved");

    const vodIds = [...new Set((insights || []).map((i) => i.vod_id))];
    let vods: DbVodSource[] = [];
    if (vodIds.length) {
      const { data: vodRows } = await sb
        .from("vod_sources")
        .select("id,bvid,title,up_name,pubdate,duration_s")
        .in("id", vodIds);
      vods = vodRows || [];
    }

    const insightsByVod: Record<string, DbCommentaryInsight[]> = {};
    for (const i of insights || []) {
      (insightsByVod[i.vod_id] ||= []).push(i as DbCommentaryInsight);
    }

    return { match: match as DbMatch, teams, vods, insightsByVod };
  } catch {
    return empty;
  }
}

export function biliUrl(bvid: string, startMs?: number): string {
  const t = startMs ? Math.max(0, Math.floor(startMs / 1000)) : 0;
  return `https://www.bilibili.com/video/${bvid}${t ? `?t=${t}` : ""}`;
}

export function fmtTimestamp(ms: number): string {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${String(sec).padStart(2, "0")}`;
}
