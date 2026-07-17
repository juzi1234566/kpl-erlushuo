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
    <article className="mx-auto max-w-2xl space-y-12">
      <Link
        href="/memes"
        className="hud-label enter inline-block transition-colors duration-500 hover:text-foreground"
      >
        ← Meme Wiki
      </Link>

      <header className="enter-1 space-y-4">
        <p className="hud-label hud-label--accent">{meme.category}</p>
        <div className="flex flex-wrap items-center gap-4">
          <h1 className="text-4xl font-extralight tracking-wide">{meme.title}</h1>
          {meme.is_ai_assisted && <span className="badge-ai">AI 辅助整理</span>}
        </div>
        <div className="hairline" />
      </header>

      <section className="enter-2 space-y-10">
        <div>
          <p className="hud-label mb-4">Definition · 释义</p>
          <p className="text-lg font-light leading-loose">{meme.definition}</p>
        </div>
        <div>
          <p className="hud-label mb-4">Origin · 出处</p>
          <p className="leading-loose text-muted">{meme.origin_story}</p>
        </div>
      </section>

      <section className="enter-3">
        <p className="hud-label mb-4">Share Card · 分享卡片</p>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={og}
          alt={`${meme.title} 卡片`}
          className="card w-full max-w-xl"
        />
      </section>
    </article>
  );
}
