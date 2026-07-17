import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import GrainOverlay from "@/components/GrainOverlay";
import Ornament from "@/components/Ornament";

export const metadata: Metadata = {
  title: "梗局 · 王者荣耀赛事玩梗社区",
  description: "面向王者荣耀职业赛事观众的粉丝玩梗社区（非官方）。赛后自动生梗、梗百科、赛程数据。",
};

const NAV = [
  { href: "/memes", label: "梗百科" },
  { href: "/matches", label: "赛程" },
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
              <span className="text-xl tracking-[0.5em]">梗局</span>
              <span className="tag hidden sm:inline">非官方粉丝社区</span>
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
            <p className="tag tag--accent text-center">梗局 · 2026 夏 · 测试版</p>
            <p className="max-w-xl text-center text-xs leading-loose text-muted">
              本站为粉丝自发社区，与腾讯、王者荣耀职业赛事及各俱乐部无隶属关系。
              AI 生成的内容一律带「AI 生成」标识。
              侵权或不适内容请发邮件至 report@example.com（上线前替换），目标 24 小时内处理。
            </p>
          </div>
        </footer>

        <GrainOverlay />
      </body>
    </html>
  );
}
