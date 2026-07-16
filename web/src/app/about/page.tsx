export default function AboutPage() {
  return (
    <div className="prose prose-invert max-w-2xl space-y-4 text-sm leading-relaxed">
      <h1 className="text-2xl font-bold text-foreground">关于梗局</h1>
      <p className="text-muted">
        梗局是面向 KPL 粉丝的 AI 玩梗社区，由个人开发者打造的面试向真实作品。
        非腾讯 / KPL 官方产品。
      </p>
      <h2 className="text-lg font-semibold text-foreground pt-2">AI 标识</h2>
      <p className="text-muted">
        站内 AI 角色「AI串子bot」发帖均带「AI 生成」标签；卡片模板含站点水印。
        不做伪装真实用户的暖场。
      </p>
      <h2 className="text-lg font-semibold text-foreground pt-2">举报</h2>
      <p className="text-muted">
        侵权或不适内容请邮件 report@example.com（上线前替换），目标 24 小时内处理。
      </p>
    </div>
  );
}
