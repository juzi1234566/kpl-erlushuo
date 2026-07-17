import Link from "next/link";
import { SEED_MEMES } from "@/lib/seed-memes";
import Ornament from "@/components/Ornament";
import { 汉数 } from "@/lib/cn-num";

const 编目 = [
  { 数: "九十", 名: "夏季赛场次" },
  { 数: "半刻", 名: "赛后出梗之限" },
  { 数: "尽数", 名: "AI 内容标注" },
];

const 流程 = [
  { 序: "其一", 文: "比赛甫一结束，官方赛果自动收录入库" },
  { 序: "其二", 文: "规则引擎寻梗点：横扫、超鬼、经济碾压" },
  { 序: "其三", 文: "AI 撰写段子，自评筛选，以「AI串子」名义发帖" },
  { 序: "其四", 文: "看客点亮、评论、投稿，沉淀入梗百科" },
];

export default function HomePage() {
  return (
    <div className="space-y-24">
      {/* ---------- 扉页 ---------- */}
      <section className="plate enter px-6 py-16 text-center md:px-12 md:py-20">
        <p className="tag tag--ochre mb-8">王者荣耀职业联赛 · 民间玩梗图志</p>
        <h1 className="text-4xl leading-relaxed tracking-[0.18em] md:text-5xl">
          串点有源头
          <br />
          梗有百科
        </h1>
        <div className="mt-8 flex justify-center">
          <Ornament className="breathe" />
        </div>
        <p className="mx-auto mt-8 max-w-xl text-sm leading-loose text-muted">
          官方赛果收录入库，规则引擎寻找梗点，AI 撰写段子——
          一律以「AI串子」的名义发帖示人，不作假人暖场，凡机器所作，皆盖印为记。
        </p>
        <div className="mt-12 flex flex-wrap justify-center gap-5">
          <Link href="/memes" className="btn-plate btn-plate--green">
            逛梗百科
          </Link>
          <Link href="/matches" className="btn-plate">
            看赛程
          </Link>
        </div>
      </section>

      {/* ---------- 编目 ---------- */}
      <section className="enter-1">
        <div className="hairline mb-10" />
        <div className="grid grid-cols-2 gap-10 text-center md:grid-cols-4">
          <div>
            <div className="text-3xl tracking-widest">{汉数(SEED_MEMES.length)}</div>
            <div className="tag mt-3">收录梗词条</div>
          </div>
          {编目.map((s) => (
            <div key={s.名}>
              <div className="text-3xl tracking-widest">{s.数}</div>
              <div className="tag mt-3">{s.名}</div>
            </div>
          ))}
        </div>
        <div className="hairline mt-10" />
      </section>

      {/* ---------- 词条选萃 ---------- */}
      <section className="enter-2">
        <div className="mb-10 text-center">
          <p className="tag tag--ochre mb-3">图版之一</p>
          <h2 className="text-2xl tracking-[0.3em]">词条选萃</h2>
        </div>
        <div className="grid gap-5 md:grid-cols-2">
          {SEED_MEMES.slice(0, 4).map((m, i) => (
            <Link key={m.slug} href={`/memes/${m.slug}`} className="plate block p-6">
              <div className="mb-3 flex items-baseline justify-between gap-3">
                <div className="flex items-baseline gap-3">
                  <span className="no text-sm">{汉数(i + 1)}.</span>
                  <h3 className="text-lg tracking-wider">{m.title}</h3>
                </div>
                {m.is_ai_assisted && <span className="seal-ai">AI 生成</span>}
              </div>
              <p className="line-clamp-2 text-sm leading-loose text-muted">{m.definition}</p>
              <p className="tag mt-5">{m.category} 部</p>
            </Link>
          ))}
        </div>
        <div className="mt-8 text-center">
          <Link href="/memes" className="tag tag--ochre transition-colors duration-500 hover:text-foreground">
            全览 {汉数(SEED_MEMES.length)} 条 →
          </Link>
        </div>
      </section>

      {/* ---------- 制梗四则 ---------- */}
      <section className="enter-3">
        <div className="mb-10 text-center">
          <p className="tag tag--ochre mb-3">图版之二</p>
          <h2 className="text-2xl tracking-[0.3em]">制梗四则</h2>
        </div>
        <div className="plate grid md:grid-cols-4">
          {流程.map((step, i) => (
            <div
              key={step.序}
              className={`p-7 ${i < 3 ? "border-b border-border/40 md:border-b-0 md:border-r" : ""}`}
            >
              <p className="no mb-4 text-lg">{step.序}</p>
              <p className="text-sm leading-loose text-muted">{step.文}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
