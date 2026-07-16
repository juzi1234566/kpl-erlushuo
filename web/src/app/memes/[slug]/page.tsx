import Link from "next/link";
import { notFound } from "next/navigation";
import { getMemeBySlug } from "@/lib/memes";
import { SEED_MEMES } from "@/lib/seed-memes";

export const dynamic = "force-dynamic";

export function generateStaticParams() {
  return SEED_MEMES.map((m) => ({ slug: m.slug }));
}

export default async function MemeDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const meme = await getMemeBySlug(slug);
  if (!meme) notFound();

  const og = `/api/og/meme-card?title=${encodeURIComponent(meme.title)}&body=${encodeURIComponent(meme.definition)}`;

  return (
    <article className="space-y-6 max-w-2xl">
      <Link href="/memes" className="text-sm text-muted hover:text-foreground">
        ← 返回梗百科
      </Link>
      <header className="space-y-2">
        <div className="flex flex-wrap gap-2 items-center">
          <h1 className="text-3xl font-bold">{meme.title}</h1>
          {meme.is_ai_assisted && (
            <span className="text-xs rounded px-2 py-0.5 bg-accent/20 text-accent">AI 辅助整理</span>
          )}
          {meme.fromDb && (
            <span className="text-xs rounded px-2 py-0.5 border border-border text-muted">DB</span>
          )}
        </div>
        <p className="text-muted text-sm">分类 · {meme.category}</p>
      </header>
      <section className="rounded-xl border border-border bg-card/50 p-5 space-y-3">
        <h2 className="font-medium">释义</h2>
        <p className="leading-relaxed">{meme.definition}</p>
        <h2 className="font-medium pt-2">出处 / 背景</h2>
        <p className="text-muted leading-relaxed">{meme.origin_story}</p>
      </section>
      <section>
        <h2 className="font-medium mb-2">分享卡片预览</h2>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={og}
          alt={`${meme.title} 卡片`}
          className="w-full max-w-xl rounded-xl border border-border"
        />
      </section>
    </article>
  );
}
