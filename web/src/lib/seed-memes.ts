import seedData from "./seed-memes.json";

export type SeedMeme = {
  slug: string;
  title: string;
  definition: string;
  origin_story: string;
  category: string;
  hotness?: number;
  is_ai_assisted?: boolean;
  tags?: string[];
};

/**
 * 种子梗词条唯一数据源：`seed-memes.json`（web 页面与 pipeline 同步脚本共用）。
 * 新增/修改词条请编辑 JSON，不要在这里写数据。
 */
export const SEED_MEMES: SeedMeme[] = seedData as SeedMeme[];

export function getMeme(slug: string) {
  return SEED_MEMES.find((m) => m.slug === slug);
}
