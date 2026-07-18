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
  verdict?: string;
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
  games_brief?: { game_no: number; one_line: string }[];
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

/** 一位解说对一场比赛的完整观点：系列赛总评 + 分局详情 */
export type CasterOpinion = {
  vod: DbVodSource;
  series: DbCommentaryInsight[]; // 整场层（overall/team/player/blame，含 games_brief）
  games: { game_no: number; page: number; rows: DbCommentaryInsight[] }[];
};

export type AggregateEntry = {
  name: string;
  text: string;
  consensus: string;
};

/** 跨解说 AI 综合评（deepseek-reasoner 生成） */
export type MatchAggregate = {
  headline: string;
  bp_read?: string;
  pace?: string;
  overall: string;
  teams: AggregateEntry[];
  players: AggregateEntry[];
  controversy?: string;
  caster_count: number;
};

export type MatchInsights = {
  match: DbMatch | null;
  teams: Record<string, DbTeam>;
  opinions: CasterOpinion[];
  aggregate: MatchAggregate | null;
};

// ---------- JSON → 行 的映射 ----------

type RawSection = {
  sentiment?: string;
  rating?: number;
  summary?: string;
  headline?: string;
  verdict?: string;
  points?: string[];
  quotes?: InsightQuote[];
} | null;

function makeRow(
  vodId: string,
  matchId: string,
  subject_type: DbCommentaryInsight["subject_type"],
  subject_name: string,
  item: RawSection,
  extra: InsightExtra = {},
  idSuffix = "",
): DbCommentaryInsight | null {
  if (!item) return null;
  const summary =
    item.headline || item.verdict || item.summary || (item.points || [])[0] || "";
  if (!summary && !(item.quotes || []).length) return null;
  return {
    id: `${vodId}-${subject_type}-${subject_name}${idSuffix}`,
    vod_id: vodId,
    match_id: matchId,
    subject_type,
    subject_name,
    sentiment: (item.sentiment as DbCommentaryInsight["sentiment"]) || "中立",
    rating: item.rating ?? null,
    summary,
    quotes: item.quotes || [],
    extra,
  };
}

/* eslint-disable @typescript-eslint/no-explicit-any */
function sectionRows(vodId: string, matchId: string, d: any, idSuffix = ""): DbCommentaryInsight[] {
  const rows: DbCommentaryInsight[] = [];
  const push = (r: DbCommentaryInsight | null) => r && rows.push(r);
  if (d.bp)
    push(
      makeRow(vodId, matchId, "bp", "BP与阵容", d.bp, {
        headline: d.bp.headline,
        points: d.bp.points || [],
        predictions: d.bp.predictions || [],
      }, idSuffix),
    );
  if (d.flow) {
    const flowSummary = [
      d.flow.early && `【前期】${d.flow.early}`,
      d.flow.mid && `【中期】${d.flow.mid}`,
      d.flow.late && `【后期】${d.flow.late}`,
    ]
      .filter(Boolean)
      .join("\n");
    push(
      makeRow(vodId, matchId, "flow", "局势走向", { ...d.flow, summary: flowSummary }, {
        turning_points: d.flow.turning_points || [],
      }, idSuffix),
    );
  }
  if (d.overall)
    push(
      makeRow(vodId, matchId, "overall", "整场比赛", d.overall, {
        headline: d.overall.headline,
        points: d.overall.points || [],
        games_brief: d.games_brief || [],
      }, idSuffix),
    );
  for (const t of d.teams || [])
    push(
      makeRow(vodId, matchId, "team", t.name, t, {
        verdict: t.verdict,
        points: t.points || [],
      }, idSuffix),
    );
  for (const p of d.players || [])
    push(
      makeRow(vodId, matchId, "player", p.name, p, {
        verdict: p.verdict,
        points: p.points || [],
        highlight: p.highlight,
        lowlight: p.lowlight,
      }, idSuffix),
    );
  if (d.blame)
    push(
      makeRow(vodId, matchId, "blame", "赛后分锅", { ...d.blame, summary: d.blame.headline }, {
        headline: d.blame.headline,
        main: d.blame.main || [],
      }, idSuffix),
    );
  if (d.golden_quotes?.length)
    push(
      makeRow(vodId, matchId, "golden", "金句时刻", {
        summary: "金句",
        sentiment: "中立",
        quotes: d.golden_quotes,
      }, {}, idSuffix),
    );
  return rows;
}

/** 本地 JSON（pipeline/data/insights）→ CasterOpinion；兼容旧单局格式 */
async function fetchLocalOpinions(matchId: string): Promise<CasterOpinion[]> {
  try {
    const { readdir, readFile } = await import("fs/promises");
    const path = await import("path");
    const dir = path.join(process.cwd(), "..", "pipeline", "data", "insights");
    const files = (await readdir(dir)).filter((f) => f.endsWith(".json") && !f.startsWith("_") && !f.endsWith(".orig.json"));
    const byCaster: Record<string, { opinion: CasterOpinion; gameCount: number }> = {};

    for (const f of files) {
      const d = JSON.parse(await readFile(path.join(dir, f), "utf-8"));
      if (String(d.match_id) !== String(matchId)) continue;
      const vodId = `local-${f}`;
      const vod: DbVodSource = {
        id: vodId,
        bvid: d.bvid,
        title: `${d.caster} 二路解说`,
        up_name: d.caster,
        caster_name: d.caster,
        page_start: Array.isArray(d.pages) ? d.pages[0] : 1,
        pubdate: null,
        duration_s: null,
      };

      let opinion: CasterOpinion;
      let gameCount: number;
      if (Array.isArray(d.games)) {
        // 新格式：分局 + 系列赛汇总
        const series = d.series
          ? sectionRows(vodId, String(matchId), {
              ...d.series,
              games_brief: d.series.games_brief,
            })
          : [];
        const games = d.games.map((g: any) => ({
          game_no: g.game_no,
          page: g.page,
          rows: sectionRows(vodId, String(matchId), g, `-g${g.game_no}`),
        }));
        opinion = { vod, series, games };
        gameCount = d.games.length;
      } else {
        // 旧格式：单局当整场——顶层内容既当 series 也当第 1 局
        const rows = sectionRows(vodId, String(matchId), d);
        opinion = {
          vod,
          series: rows.filter((r) =>
            ["overall", "team", "player", "blame"].includes(r.subject_type),
          ),
          games: [{ game_no: 1, page: vod.page_start || 1, rows }],
        };
        gameCount = 1;
      }

      const prev = byCaster[d.caster];
      if (!prev || gameCount > prev.gameCount) {
        byCaster[d.caster] = { opinion, gameCount };
      }
    }
    return Object.values(byCaster).map((x) => x.opinion);
  } catch {
    return [];
  }
}
/* eslint-enable @typescript-eslint/no-explicit-any */

async function fetchLocalAggregate(matchId: string): Promise<MatchAggregate | null> {
  try {
    const { readFile } = await import("fs/promises");
    const path = await import("path");
    const p = path.join(
      process.cwd(), "..", "pipeline", "data", "insights", `_match_${matchId}.json`,
    );
    const d = JSON.parse(await readFile(p, "utf-8"));
    return {
      headline: d.headline || "",
      bp_read: d.bp_read || "",
      pace: d.pace || "",
      overall: d.overall || "",
      teams: d.teams || [],
      players: d.players || [],
      controversy: d.controversy || "",
      caster_count: d.caster_count || 0,
    };
  } catch {
    return null;
  }
}

/** 比赛详情 + 各解说观点（比赛信息走云端，观点当前本地模式） */
export async function fetchMatchInsights(matchId: string): Promise<MatchInsights> {
  const empty: MatchInsights = { match: null, teams: {}, opinions: [], aggregate: null };
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

    const opinions = await fetchLocalOpinions(matchId);
    const aggregate = await fetchLocalAggregate(matchId);
    return { match: match as DbMatch, teams, opinions, aggregate };
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

// ---------- 选手档案 ----------

export type PlayerReview = {
  match_id: string;
  caster: string;
  bvid: string;
  page_start: number | null;
  sentiment: DbCommentaryInsight["sentiment"];
  rating: number | null;
  verdict: string;
  points: string[];
  quotes: InsightQuote[];
};

/** 某选手的跨场次跨主播评价（整场层优先；本地模式） */
export async function fetchPlayerReviews(name: string): Promise<PlayerReview[]> {
  try {
    const { readdir, readFile } = await import("fs/promises");
    const path = await import("path");
    const dir = path.join(process.cwd(), "..", "pipeline", "data", "insights");
    const files = (await readdir(dir)).filter((f) => f.endsWith(".json") && !f.startsWith("_") && !f.endsWith(".orig.json"));
    const best: Record<string, { review: PlayerReview; games: number }> = {};
    for (const f of files) {
      /* eslint-disable-next-line @typescript-eslint/no-explicit-any */
      const d: any = JSON.parse(await readFile(path.join(dir, f), "utf-8"));
      const key = `${d.match_id}:${d.caster}`;
      const games = Array.isArray(d.games) ? d.games.length : 1;
      const source = d.series || d; // 新格式取系列赛层，旧格式取顶层
      for (const pl of source?.players || []) {
        if (pl.name !== name) continue;
        const review: PlayerReview = {
          match_id: String(d.match_id),
          caster: d.caster,
          bvid: d.bvid,
          page_start: Array.isArray(d.pages) ? d.pages[0] : 1,
          sentiment: pl.sentiment || "中立",
          rating: pl.rating ?? null,
          verdict: pl.verdict || "",
          points: pl.points || [],
          quotes: pl.quotes || [],
        };
        if (!best[key] || games > best[key].games) best[key] = { review, games };
      }
    }
    return Object.values(best).map((x) => x.review);
  } catch {
    return [];
  }
}

// ---------- 首页：已出观点的比赛 ----------

export type AnalyzedMatch = {
  match_id: string;
  casters: string[];
  match: DbMatch | null;
  teamNames: string[];
};

export async function listAnalyzedMatches(): Promise<AnalyzedMatch[]> {
  const byMatch: Record<string, Set<string>> = {};
  try {
    const { readdir, readFile } = await import("fs/promises");
    const path = await import("path");
    const dir = path.join(process.cwd(), "..", "pipeline", "data", "insights");
    const files = (await readdir(dir)).filter((f) => f.endsWith(".json") && !f.startsWith("_") && !f.endsWith(".orig.json"));
    for (const f of files) {
      const d = JSON.parse(await readFile(path.join(dir, f), "utf-8"));
      if (d.match_id) (byMatch[String(d.match_id)] ||= new Set()).add(d.caster);
    }
  } catch {
    /* 目录不存在则为空 */
  }

  const sb = getSupabase();
  const out: AnalyzedMatch[] = [];
  for (const id of Object.keys(byMatch)) {
    let match: DbMatch | null = null;
    const teamNames: string[] = [];
    if (sb) {
      try {
        const { data } = await sb
          .from("matches")
          .select("id,team1_id,team2_id,score1,score2,bo,status,start_time,stage_name,stage_desc")
          .eq("id", id)
          .maybeSingle();
        match = (data as DbMatch) || null;
        if (match) {
          const tids = [match.team1_id, match.team2_id].filter(Boolean) as string[];
          const { data: ts } = await sb.from("teams").select("id,name").in("id", tids);
          for (const tid of tids) teamNames.push(ts?.find((t) => t.id === tid)?.name || "");
        }
      } catch {
        /* ignore */
      }
    }
    out.push({ match_id: id, casters: [...byMatch[id]], match, teamNames });
  }
  out.sort((a, b) => (b.match?.start_time || "").localeCompare(a.match?.start_time || ""));
  return out;
}
