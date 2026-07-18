import type { DbCommentaryInsight, DbVodSource } from "./insights";

export type ConsensusItem = {
  kind: "共识好评" | "共识差评" | "两极分化";
  subject_name: string;
  subject_type: "team" | "player";
  detail: string; // 如「可温★5 · 时间★4」或「可温★5 vs 时间★2」
  casterCount: number;
};

/** 跨主播聚合：全员同向 = 共识；好评差评并存 = 两极分化 */
export function buildConsensus(
  vods: DbVodSource[],
  insightsByVod: Record<string, DbCommentaryInsight[]>,
): ConsensusItem[] {
  const casterOf: Record<string, string> = {};
  for (const v of vods) casterOf[v.id] = v.caster_name || v.up_name || "解说";

  type Vote = { caster: string; sentiment: string; rating: number | null };
  const bySubject: Record<string, { type: "team" | "player"; votes: Vote[] }> = {};

  for (const [vodId, list] of Object.entries(insightsByVod)) {
    for (const i of list) {
      if (i.subject_type !== "team" && i.subject_type !== "player") continue;
      const key = `${i.subject_type}:${i.subject_name}`;
      (bySubject[key] ||= { type: i.subject_type, votes: [] }).votes.push({
        caster: casterOf[vodId] || "解说",
        sentiment: i.sentiment,
        rating: i.rating,
      });
    }
  }

  const items: ConsensusItem[] = [];
  const fmt = (v: Vote) => `${v.caster}${v.rating ? `★${v.rating}` : ""}`;

  for (const [key, { type, votes }] of Object.entries(bySubject)) {
    if (votes.length < 2) continue; // 单一来源谈不上共识
    const name = key.split(":")[1];
    const goods = votes.filter((v) => v.sentiment === "好评");
    const bads = votes.filter((v) => v.sentiment === "差评");

    if (goods.length && bads.length) {
      items.push({
        kind: "两极分化",
        subject_name: name,
        subject_type: type,
        detail: `${goods.map(fmt).join("、")} vs ${bads.map(fmt).join("、")}`,
        casterCount: votes.length,
      });
    } else if (goods.length === votes.length) {
      items.push({
        kind: "共识好评",
        subject_name: name,
        subject_type: type,
        detail: votes.map(fmt).join(" · "),
        casterCount: votes.length,
      });
    } else if (bads.length === votes.length) {
      items.push({
        kind: "共识差评",
        subject_name: name,
        subject_type: type,
        detail: votes.map(fmt).join(" · "),
        casterCount: votes.length,
      });
    }
  }

  // 两极分化最有戏，排前面；同类按参与主播数降序
  const order = { 两极分化: 0, 共识差评: 1, 共识好评: 2 };
  items.sort((a, b) => order[a.kind] - order[b.kind] || b.casterCount - a.casterCount);
  return items;
}
