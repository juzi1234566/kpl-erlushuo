const SECTIONS = [
  {
    code: "01 / WHAT",
    title: "这是什么",
    body: "梗局是面向 KPL 粉丝的 AI 玩梗社区，由个人开发者打造的面试向真实作品。非腾讯 / KPL 官方产品，与任何俱乐部无隶属关系。",
  },
  {
    code: "02 / AI",
    title: "AI 标识",
    body: "站内 AI 角色「AI串子bot」发帖均带「AI 生成」标签；分享卡片模板含站点水印。不做伪装真实用户的暖场。",
  },
  {
    code: "03 / REPORT",
    title: "举报",
    body: "侵权或不适内容请邮件 report@example.com（上线前替换），目标 24 小时内处理。",
  },
];

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-14">
      <header className="enter">
        <p className="hud-label mb-3">About</p>
        <h1 className="text-3xl font-extralight tracking-wide">关于梗局</h1>
      </header>

      <div className="enter-1 space-y-12">
        {SECTIONS.map((s) => (
          <section key={s.code}>
            <p className="hud-label hud-label--accent mb-3">{s.code}</p>
            <h2 className="mb-4 text-xl font-extralight tracking-wide">{s.title}</h2>
            <p className="text-sm leading-loose text-muted">{s.body}</p>
            <div className="hairline mt-10" />
          </section>
        ))}
      </div>
    </div>
  );
}
