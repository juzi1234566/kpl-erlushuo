import { createClient, SupabaseClient } from "@supabase/supabase-js";

let browserClient: SupabaseClient | null = null;

export function getSupabase(): SupabaseClient | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return null;
  if (typeof window === "undefined") {
    return createClient(url, key);
  }
  if (!browserClient) browserClient = createClient(url, key);
  return browserClient;
}

export function hasSupabaseEnv(): boolean {
  return Boolean(
    process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  );
}

export type DbMeme = {
  id: string;
  slug: string;
  title: string;
  definition: string;
  origin_story: string | null;
  category: string | null;
  is_ai_assisted: boolean | null;
  hotness: number | null;
};
