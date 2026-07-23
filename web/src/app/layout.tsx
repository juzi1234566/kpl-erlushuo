import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import GrainOverlay from "@/components/GrainOverlay";
import Ornament from "@/components/Ornament";
import FeedbackWidget from "@/components/FeedbackWidget";

export const metadata: Metadata = {
  title: "KPL二路说 · 二路解说观点聚合",
  description:
    "比赛打得怎么样，听二路解说怎么说。AI 自动聚合各家二路视频观点：BP 点评、选手评价、赛后复盘、金句时刻（非官方粉丝站）。",
};

const NAV = [
  { href: "/matches", label: "赛程与观点" },
  { href: "/about", label: "关于" },
];

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">
        <header className="sticky top-0 z-20 border-b border-border bg-background/85 backdrop-blur-sm">
          <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-5">
            <Link href="/" className="flex items-baseline gap-4">
              <span className="text-xl tracking-[0.2em]">KPL二路说</span>
              <span className="tag hidden sm:inline">非官方粉丝站</span>
            </Link>
            <nav className="flex items-center gap-8">
              {NAV.map((n) => (
                <Link
                  key={n.href}
                  href={n.href}
                  className="tag transition-colors duration-500 hover:text-foreground"
                >
                  {n.label}
                </Link>
              ))}
            </nav>
          </div>
          <div className="hairline" />
        </header>

        <main className="mx-auto min-h-[70vh] max-w-5xl px-5 py-14">{children}</main>

        <footer className="mt-24 pb-12">
          <div className="mx-auto flex max-w-5xl flex-col items-center gap-6 px-5">
            <Ornament className="breathe" />
            <p className="tag tag--accent text-center">KPL二路说 · 2026 夏 · 测试版</p>
            <p className="max-w-xl text-center text-xs leading-loose text-muted">
              本站为粉丝自发项目，与腾讯、王者荣耀职业赛事、各俱乐部及各解说均无隶属关系。
              观点由 AI 自动提取自各解说公开视频，引用归属原作者，点击时间戳可跳转原视频；AI
              内容一律带标识。侵权或不适内容请发邮件至 3365132306@qq.com，目标 24
              小时内处理。
            </p>
          </div>
        </footer>

        <FeedbackWidget />
        <GrainOverlay />
      </body>
    </html>
  );
}
