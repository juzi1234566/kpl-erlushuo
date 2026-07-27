import { SEED_MEMES, type SeedMeme } from "./seed-memes";
import { getSupabase, type DbMeme } from "./supabase";

export type MemeView = SeedMeme & { fromDb?: boolean };

function mapDb(m: DbMeme): MemeView {
  return {
    slug: m.slug,
    title: m.title,
    definition: m.definition,
    origin_story: m.origin_story || "",
    category: m.category || "未分类",
    is_ai_assisted: Boolean(m.is_ai_assisted),
    fromDb: true,
  };
}

/** 有 Supabase 就读库，失败或未配置则回落种子数据 */
export async function listMemes(): Promise<MemeView[]> {
  const sb = getSupabase();
  if (!sb) return SEED_MEMES.map((m) => ({ ...m, fromDb: false }));
  try {
    const { data, error } = await sb
      .from("memes")
      .select("id,slug,title,definition,origin_story,category,is_ai_assisted,hotness")
      .eq("moderation_status", "approved")
      .is("deleted_at", null)
      .order("hotness", { ascending: false });
    if (error || !data?.length) {
      return SEED_MEMES.map((m) => ({ ...m, fromDb: false }));
    }
    return data.map(mapDb);
  } catch {
    return SEED_MEMES.map((m) => ({ ...m, fromDb: false }));
  }
}

export async function getMemeBySlug(slug: string): Promise<MemeView | null> {
  const sb = getSupabase();
  if (sb) {
    try {
      const { data, error } = await sb
        .from("memes")
        .select("id,slug,title,definition,origin_story,category,is_ai_assisted,hotness")
        .eq("slug", slug)
        .maybeSingle();
      if (!error && data) return mapDb(data as DbMeme);
    } catch {
      /* fall through */
    }
  }
  const seed = SEED_MEMES.find((m) => m.slug === slug);
  return seed ? { ...seed, fromDb: false } : null;
}
