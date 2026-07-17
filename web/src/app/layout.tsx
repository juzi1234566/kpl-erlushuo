import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import GrainOverlay from "@/components/GrainOverlay";
import Ornament from "@/components/Ornament";

export const metadata: Metadata = {
  title: "梗局 · 王者荣耀赛事玩梗图志",
  description: "面向王者荣耀职业联赛观众的粉丝玩梗社区（非官方）。赛后自动生梗、梗百科、赛程数据。",
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
              <span className="tag hidden sm:inline">非官方 · 粉丝社群</span>
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
            <p className="tag tag--ochre text-center">
              梗局 · 丙午年夏 · 试运行第一版
            </p>
            <p className="max-w-xl text-center text-xs leading-loose text-muted">
              本站为粉丝自发社区，与腾讯、王者荣耀职业联赛及各俱乐部并无隶属关系。
              人工智能生成的内容一律盖「AI 生成」印为记。
              侵权或不适内容请致信 report@example.com（上线前替换），当日受理。
            </p>
          </div>
        </footer>

        <GrainOverlay />
      </body>
    </html>
  );
}
