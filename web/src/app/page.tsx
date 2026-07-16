import Link from "next/link";
import { SEED_MEMES } from "@/lib/seed-memes";

export default function HomePage() {
  return (
    <div className="space-y-10">
      <section className="rounded-2xl border border-border bg-card/60 p-8 md:p-10">
        <p className="text-accent-2 text-sm mb-3">AI Native · 赛后 30 分钟内出梗</p>
        <h1 className="text-3xl md:text-4xl font-bold leading-tight">
          串点有源头，梗有百科
          <br />
          <span className="text-muted text-2xl md:text-3xl font-medium">
            KPL 粉丝的垂直玩梗社区
          </span>
        </h1>
        <p className="mt-4 max-w-2xl text-muted leading-relaxed">
          官方开放赛果入库 → 规则找梗点 → AI 写段子 → 以「AI串子bot」身份发帖。
          不做假用户暖场，AI 标识 100% 覆盖。
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            href="/memes"
            className="rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-white hover:opacity-90"
          >
            逛梗百科
          </Link>
          <Link
            href="/matches"
            className="rounded-full border border-border px-5 py-2.5 text-sm hover:border-accent"
          >
            看赛程数据
          </Link>
        </div>
      </section>

      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">种子梗词条</h2>
          <Link href="/memes" className="text-sm text-accent">
            全部 →
          </Link>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          {SEED_MEMES.slice(0, 4).map((m) => (
            <Link
              key={m.slug}
              href={`/memes/${m.slug}`}
              className="rounded-xl border border-border bg-card/40 p-4 hover:border-accent/60 transition"
            >
              <div className="flex items-center gap-2 mb-1">
                <h3 className="font-medium">{m.title}</h3>
                {m.is_ai_assisted && (
                  <span className="text-[10px] rounded px-1.5 py-0.5 bg-accent/20 text-accent">
                    AI 辅助
                  </span>
                )}
              </div>
              <p className="text-sm text-muted line-clamp-2">{m.definition}</p>
            </Link>
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-border bg-card/30 p-5 text-sm text-muted">
        <h2 className="text-foreground font-medium mb-2">MVP 核心闭环</h2>
        <ol className="list-decimal list-inside space-y-1">
          <li>比赛结束 → 赛事管线入库</li>
          <li>规则引擎算梗点（横扫 / 超鬼 / 经济碾压…）</li>
          <li>DeepSeek 生成候选 → 自评 → bot 发帖</li>
          <li>用户点亮 / 评论 / 投稿 → 沉淀百科</li>
        </ol>
      </section>
    </div>
  );
}
