import Link from "next/link";
import { listMemes } from "@/lib/memes";
import { hasSupabaseEnv } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export default async function MemesPage() {
  const memes = await listMemes();
  const fromDb = memes.some((m) => m.fromDb);

  return (
    <div className="space-y-10">
      <header className="enter">
        <p className="hud-label mb-3 flex items-center gap-3">
          <span className="dot-live" />
          Meme Wiki · {memes.length} entries
        </p>
        <h1 className="text-3xl font-extralight tracking-wide">梗百科</h1>
        <p className="mt-3 text-xs text-faint">
          {fromDb ? "数据来自 Supabase" : "本地种子（配置 Supabase 后自动读库）"}
          {!hasSupabaseEnv() && " · 未检测到 NEXT_PUBLIC_SUPABASE_* 环境变量"}
        </p>
      </header>

      <div className="enter-1 grid gap-4 md:grid-cols-2">
        {memes.map((m) => (
          <Link key={m.slug} href={`/memes/${m.slug}`} className="card group block p-6">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h2 className="text-lg font-light tracking-wide">{m.title}</h2>
              {m.is_ai_assisted && <span className="badge-ai">AI</span>}
            </div>
            <p className="line-clamp-2 text-sm leading-relaxed text-muted">{m.definition}</p>
            <p className="hud-label mt-4">{m.category}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
