import Link from "next/link";
import { listMemes } from "@/lib/memes";

export const dynamic = "force-dynamic";

export default async function MemesPage() {
  const memes = await listMemes();
  const fromDb = memes.some((m) => m.fromDb);

  return (
    <div className="space-y-12">
      <header className="enter text-center">
        <p className="tag tag--accent mb-4">共 {memes.length} 条</p>
        <h1 className="text-3xl tracking-[0.3em]">梗百科</h1>
        <p className="mt-4 text-xs text-faint">
          {fromDb ? "数据实时读取自云端词库" : "暂为本地数据（联库后自动更新）"}
        </p>
      </header>

      <div className="enter-1 grid gap-5 md:grid-cols-2">
        {memes.map((m, i) => (
          <Link key={m.slug} href={`/memes/${m.slug}`} className="plate block p-6">
            <div className="mb-3 flex items-baseline justify-between gap-3">
              <div className="flex items-baseline gap-3">
                <span className="no text-sm">{i + 1}.</span>
                <h2 className="text-lg tracking-wider">{m.title}</h2>
              </div>
              {m.is_ai_assisted && <span className="seal-ai">AI 生成</span>}
            </div>
            <p className="line-clamp-2 text-sm leading-loose text-muted">{m.definition}</p>
            <p className="tag mt-5">{m.category}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
