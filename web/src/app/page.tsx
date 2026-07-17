import Link from "next/link";
import { SEED_MEMES } from "@/lib/seed-memes";
import HeroCanvas from "@/components/HeroCanvas";

const STATS = [
  { value: String(SEED_MEMES.length), label: "梗词条" },
  { value: "90", label: "夏季赛场次" },
  { value: "30min", label: "赛后出梗窗口" },
  { value: "100%", label: "AI 内容标识" },
];

const LOOP = [
  { code: "01 / INGEST", text: "比赛结束，官方赛果自动入库" },
  { code: "02 / SIGNAL", text: "规则引擎找梗点：横扫 · 超鬼 · 经济碾压" },
  { code: "03 / GENERATE", text: "AI 写段子，自评过滤，以 bot 身份发帖" },
  { code: "04 / COMMUNITY", text: "点亮 · 评论 · 投稿，沉淀进梗百科" },
];

export default function HomePage() {
  return (
    <div className="space-y-24">
      {/* ---------- Hero ---------- */}
      <section className="relative -mx-5 -mt-12 overflow-hidden px-5 pb-24 pt-28 md:pt-36">
        <HeroCanvas />
        <div className="relative mx-auto max-w-5xl">
          <p className="hud-label hud-label--accent enter mb-8 flex items-center gap-3">
            <span className="dot-live" />
            AI Native · 赛后 30 分钟出梗
          </p>
          <h1 className="enter-1 text-4xl font-extralight leading-[1.25] tracking-wide md:text-6xl">
            串点有源头
            <br />
            <span className="glow-text">梗</span>有百科
          </h1>
          <p className="enter-2 mt-8 max-w-xl text-sm leading-loose text-muted md:text-base">
            KPL 粉丝的垂直玩梗社区。官方赛果入库，规则引擎找梗点，AI
            写段子——全部以「AI串子bot」的身份发帖，不做假用户暖场。
          </p>
          <div className="enter-3 mt-12 flex flex-wrap gap-4">
            <Link href="/memes" className="btn-ghost">
              逛梗百科
            </Link>
            <Link href="/matches" className="btn-ghost btn-ghost--dim">
              赛程数据
            </Link>
          </div>
        </div>
      </section>

      {/* ---------- 数据行 ---------- */}
      <section className="enter-3">
        <div className="hairline mb-10" />
        <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
          {STATS.map((s) => (
            <div key={s.label}>
              <div className="text-3xl font-extralight tracking-wider text-foreground/90">
                {s.value}
              </div>
              <div className="hud-label mt-2">{s.label}</div>
            </div>
          ))}
        </div>
        <div className="hairline mt-10" />
      </section>

      {/* ---------- 精选词条 ---------- */}
      <section>
        <div className="mb-8 flex items-end justify-between">
          <div>
            <p className="hud-label mb-2">Meme Wiki</p>
            <h2 className="text-2xl font-extralight tracking-wide">梗词条</h2>
          </div>
          <Link
            href="/memes"
            className="hud-label transition-colors duration-500 hover:text-foreground"
          >
            全部 {SEED_MEMES.length} 条 →
          </Link>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {SEED_MEMES.slice(0, 4).map((m) => (
            <Link key={m.slug} href={`/memes/${m.slug}`} className="card group block p-6">
              <div className="mb-3 flex items-center justify-between gap-2">
                <h3 className="text-lg font-light tracking-wide">{m.title}</h3>
                {m.is_ai_assisted && <span className="badge-ai">AI</span>}
              </div>
              <p className="line-clamp-2 text-sm leading-relaxed text-muted">{m.definition}</p>
              <p className="hud-label mt-4">{m.category}</p>
            </Link>
          ))}
        </div>
      </section>

      {/* ---------- 核心闭环 ---------- */}
      <section>
        <p className="hud-label mb-2">Pipeline</p>
        <h2 className="mb-10 text-2xl font-extralight tracking-wide">从赛果到梗的闭环</h2>
        <div className="grid gap-px overflow-hidden rounded-md border border-border bg-border md:grid-cols-4">
          {LOOP.map((step) => (
            <div key={step.code} className="bg-background p-6">
              <p className="hud-label hud-label--accent mb-4">{step.code}</p>
              <p className="text-sm leading-relaxed text-muted">{step.text}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
