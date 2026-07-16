export type SeedMeme = {
  slug: string;
  title: string;
  definition: string;
  origin_story: string;
  category: string;
  is_ai_assisted?: boolean;
  tags?: string[];
};

/** 上线前持续补到 ≥50；此处先放种子便于页面联调 */
export const SEED_MEMES: SeedMeme[] = [
  {
    slug: "san-bi-ling",
    title: "三比零",
    definition: "系列赛 3:0 横扫，常用来形容一边倒或「来都来了不如体面点」。",
    origin_story: "KPL 常规赛/季后赛高频比分叙事，评论区模板句。",
    category: "赛果",
    tags: ["横扫", "BO5"],
  },
  {
    slug: "chao-gui",
    title: "超鬼",
    definition: "对线/团战表现极差，KDA 难看到离谱时的统称。",
    origin_story: "观众弹幕与虎扑串子常用黑话，后被解说偶尔玩梗引用。",
    category: "选手",
    tags: ["KDA", "黑话"],
  },
  {
    slug: "jue-huo",
    title: "绝活",
    definition: "选手招牌英雄或独特理解，ban 掉等于砍半条命。",
    origin_story: "BP 环节「绝活被 ban」是赛后复盘与玩梗的经典入口。",
    category: "BP",
    tags: ["英雄池", "BP"],
  },
  {
    slug: "rang-er-zhui-san",
    title: "让二追三",
    definition: "先落后 0-2，再连下三局 3-2 翻盘。",
    origin_story: "戏剧性系列赛叙事，二路解说最爱的剧本之一。",
    category: "赛果",
    tags: ["翻盘", "BO5"],
  },
  {
    slug: "ai-chuan-zi-bot",
    title: "AI串子bot",
    definition: "本站官方 AI 角色：明确标注 AI，只负责赛后整活，不装真人。",
    origin_story: "为合规与产品差异化设计的 bot 人设，替代「假用户暖场」。",
    category: "站务",
    is_ai_assisted: true,
    tags: ["AI", "合规"],
  },
  {
    slug: "sai-hou-huang-jin-30fen",
    title: "赛后黄金 30 分钟",
    definition: "比赛刚结束时梗的产出与传播效率最高的时间窗。",
    origin_story: "垂直社区运营共识；本产品把自动化生梗对准这个窗口。",
    category: "站务",
    is_ai_assisted: true,
    tags: ["运营", "AI"],
  },
];

export function getMeme(slug: string) {
  return SEED_MEMES.find((m) => m.slug === slug);
}
