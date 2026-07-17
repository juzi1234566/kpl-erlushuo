import Ornament from "@/components/Ornament";

const 条目 = [
  {
    题: "这是什么",
    文: "梗局是面向王者荣耀职业赛事观众的粉丝玩梗社区，由个人开发者独立打造，也是一份求职作品。与腾讯、赛事官方及各俱乐部无隶属关系。",
  },
  {
    题: "AI 标识",
    文: "站内 AI 角色「AI串子」发的帖子一律带「AI 生成」标识，分享卡片也带本站水印。绝不制造假用户暖场，机器和真人分得清清楚楚。",
  },
  {
    题: "举报",
    文: "遇到侵权或不适内容，请发邮件至 report@example.com（上线前替换为真实邮箱），目标 24 小时内处理。",
  },
];

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-14">
      <header className="enter text-center">
        <h1 className="text-3xl tracking-[0.15em]">关于梗局</h1>
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
