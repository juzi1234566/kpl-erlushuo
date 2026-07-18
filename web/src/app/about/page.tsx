import Ornament from "@/components/Ornament";

const 条目 = [
  {
    题: "这是什么",
    文: "看完一场比赛想知道「专业的人怎么评」，二路解说视频是最好的答案——但每场比赛有十几家二路，谁也看不完。KPL二路说用 AI 自动听完各家视频，把观点整理成几分钟能看完的赛评：BP 点评、选手评价、赛后分锅、金句时刻。由个人开发者独立打造，非官方项目。",
  },
  {
    题: "观点属于解说，AI 只做整理",
    文: "所有观点都提取自各解说的公开视频，引用标注来源、点击时间戳可跳转原视频对应位置。AI 整理的内容一律带「AI 提取」标识；转写可能有误，以原视频为准。如解说本人不希望内容被收录，联系我们立即下架。",
  },
  {
    题: "举报与联系",
    文: "侵权或不适内容，请发邮件至 3365132306@qq.com，目标 24 小时内处理。",
  },
];

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-14">
      <header className="enter text-center">
        <h1 className="text-3xl tracking-[0.15em]">关于 KPL二路说</h1>
        <div className="mt-7 flex justify-center">
          <Ornament className="breathe" />
        </div>
      </header>

      <div className="enter-1 space-y-10">
        {条目.map((s, i) => (
          <section key={s.题} className="plate px-7 py-8 md:px-10">
            <p className="no mb-3">{i + 1}</p>
            <h2 className="mb-4 text-xl tracking-[0.1em]">{s.题}</h2>
            <p className="text-[15px] leading-loose text-muted">{s.文}</p>
          </section>
        ))}
      </div>
    </div>
  );
}
