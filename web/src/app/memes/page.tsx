import Link from "next/link";
import { listMemes } from "@/lib/memes";
import { hasSupabaseEnv } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export default async function MemesPage() {
  const memes = await listMemes();
  const fromDb = memes.some((m) => m.fromDb);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">梗百科</h1>
        <p className="text-muted text-sm mt-1">
          共 {memes.length} 条
          {fromDb ? " · 数据来自 Supabase" : " · 本地种子（配置 Supabase 后自动读库）"}
          {!hasSupabaseEnv() && " · 未检测到 NEXT_PUBLIC_SUPABASE_* 环境变量"}
        </p>
      </div>
      <div className="grid gap-3">
        {memes.map((m) => (
          <Link
            key={m.slug}
            href={`/memes/${m.slug}`}
            className="rounded-xl border border-border bg-card/50 p-4 hover:border-accent/50"
          >
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="font-semibold">{m.title}</h2>
              <span className="text-xs text-muted border border-border rounded px-1.5">
                {m.category}
              </span>
              {m.is_ai_assisted && (
                <span className="text-[10px] rounded px-1.5 py-0.5 bg-accent/20 text-accent">
                  AI 辅助
                </span>
              )}
            </div>
            <p className="text-sm text-muted mt-2">{m.definition}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
