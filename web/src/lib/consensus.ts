import type { CasterOpinion } from "./insights";

export type RatingCell = {
  rating: number | null;
  sentiment: string;
};

export type RatingRow = {
  subject_name: string;
  subject_type: "team" | "player";
  cells: Record<string, RatingCell>; // 解说名 → 打分
  verdict: string; // 一句总体评价
  avg: number; // 排序用
};

export type RatingTable = {
  casters: string[];
  rows: RatingRow[];
};

/** 一句总体评价：从各家情绪分布直接得出 */
function overallVerdict(cells: RatingCell[]): string {
  const goods = cells.filter((c) => c.sentiment === "好评").length;
  const bads = cells.filter((c) => c.sentiment === "差评").length;
  const n = cells.length;
  if (goods === n && n >= 2) return "一致好评";
  if (bads === n && n >= 2) return "一致差评";
  if (goods > 0 && bads > 0) return "褒贬不一";
  if (goods > 0) return "偏好评";
  if (bads > 0) return "偏差评";
  return "中规中矩";
}

/** 打分表：行=战队/选手，列=各解说的整场星级 */
export function buildRatingTable(opinions: CasterOpinion[]): RatingTable {
  const casters = opinions.map((o) => o.vod.caster_name || o.vod.up_name || "解说");

  const rowMap: Record<string, RatingRow> = {};
  for (const o of opinions) {
    const caster = o.vod.caster_name || o.vod.up_name || "解说";
    for (const i of o.series) {
      if (i.subject_type !== "team" && i.subject_type !== "player") continue;
      const key = `${i.subject_type}:${i.subject_name}`;
      const row = (rowMap[key] ||= {
        subject_name: i.subject_name,
        subject_type: i.subject_type,
        cells: {},
        verdict: "",
        avg: 0,
      });
      row.cells[caster] = { rating: i.rating, sentiment: i.sentiment };
    }
  }

  const rows = Object.values(rowMap);
  for (const row of rows) {
    const cells = Object.values(row.cells);
    row.verdict = overallVerdict(cells);
    const rated = cells.filter((c) => c.rating);
    row.avg = rated.length
      ? rated.reduce((s, c) => s + (c.rating || 0), 0) / rated.length
      : 0;
  }

  // 战队在前；同类按平均分降序
  rows.sort(
    (a, b) =>
      (a.subject_type === "team" ? 0 : 1) - (b.subject_type === "team" ? 0 : 1) ||
      b.avg - a.avg,
  );
  return { casters, rows };
}
