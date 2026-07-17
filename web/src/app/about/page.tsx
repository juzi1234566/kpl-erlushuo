import Ornament from "@/components/Ornament";

const 条目 = [
  {
    序: "其一",
    题: "本站缘起",
    文: "梗局是面向王者荣耀职业联赛观众的粉丝玩梗社区，由个人开发者一人所作，用作求职期间的真实作品。与腾讯、职业联赛官方及各俱乐部并无隶属关系。",
  },
  {
    序: "其二",
    题: "机器所作，盖印为记",
    文: "站内 AI 角色「AI串子」所发帖子，一律盖「AI 生成」朱印；分享卡片亦带本站水印。绝不制造假用户暖场，机器与真人，泾渭分明。",
  },
  {
    序: "其三",
    题: "举报与受理",
    文: "如遇侵权或不适内容，请致信 report@example.com（上线前替换为真实邮箱），本站当日受理，目标二十四小时内处置。",
  },
];

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-14">
      <header className="enter text-center">
        <p className="tag tag--ochre mb-4">识语</p>
        <h1 className="text-3xl tracking-[0.3em]">关于梗局</h1>
        <div className="mt-7 flex justify-center">
          <Ornament className="breathe" />
        </div>
      </header>

      <div className="enter-1 space-y-10">
        {条目.map((s) => (
          <section key={s.序} className="plate px-7 py-8 md:px-10">
            <p className="no mb-3">{s.序}</p>
            <h2 className="mb-4 text-xl tracking-[0.2em]">{s.题}</h2>
            <p className="text-sm leading-loose text-muted">{s.文}</p>
          </section>
        ))}
      </div>
    </div>
  );
}
