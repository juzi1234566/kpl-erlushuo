import Link from "next/link";
import { notFound } from "next/navigation";
import { getMemeBySlug } from "@/lib/memes";
import { SEED_MEMES } from "@/lib/seed-memes";
import Ornament from "@/components/Ornament";

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
        className="tag enter inline-block transition-colors duration-500 hover:text-foreground"
      >
        ← 返回梗百科
      </Link>

      <header className="enter-1 text-center">
        <p className="tag tag--accent mb-5">{meme.category}</p>
        <div className="flex flex-wrap items-center justify-center gap-4">
          <h1 className="text-4xl tracking-[0.1em]">{meme.title}</h1>
          {meme.is_ai_assisted && <span className="seal-ai">AI 生成</span>}
        </div>
        <div className="mt-7 flex justify-center">
          <Ornament className="breathe" />
        </div>
      </header>

      <section className="plate enter-2 space-y-10 px-7 py-9 md:px-10">
        <div>
          <p className="tag tag--accent mb-4">释义</p>
          <p className="text-lg leading-loose">{meme.definition}</p>
        </div>
        <div className="hairline" />
        <div>
          <p className="tag tag--accent mb-4">出处</p>
          <p className="leading-loose text-muted">{meme.origin_story}</p>
        </div>
      </section>

      <section className="enter-3">
        <p className="tag tag--accent mb-4 text-center">分享卡片</p>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={og} alt={`${meme.title} 分享卡片`} className="plate w-full" />
      </section>
    </article>
  );
}
