import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "梗局 · KPL 粉丝玩梗社区",
  description: "AI 驱动的 KPL 垂直玩梗社区（非官方）。赛后自动生梗、梗百科、选手页。",
};

const NAV = [
  { href: "/memes", label: "梗百科", code: "WIKI" },
  { href: "/matches", label: "赛程", code: "MATCHES" },
  { href: "/about", label: "关于", code: "ABOUT" },
];

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <header className="sticky top-0 z-40 border-b border-border bg-background/60 backdrop-blur-md">
          <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-5">
            <Link href="/" className="flex items-baseline gap-3">
              <span className="text-lg font-extralight tracking-[0.3em]">
                <span className="glow-text">梗</span>局
              </span>
              <span className="hud-label hidden sm:inline">Unofficial · Fan Community</span>
            </Link>
            <nav className="flex items-center gap-7">
              {NAV.map((n) => (
                <Link
                  key={n.href}
                  href={n.href}
                  className="hud-label transition-colors duration-500 hover:text-foreground"
                >
                  {n.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>

        <main className="mx-auto min-h-[70vh] max-w-5xl px-5 py-12">{children}</main>

        <footer className="mt-24">
          <div className="hairline" />
          <div className="mx-auto max-w-5xl space-y-4 px-5 py-10">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span className="hud-label">梗局 · Geng Ju</span>
              <span className="hud-label">KPL-MEME / MVP v0.1</span>
            </div>
            <p className="text-xs leading-relaxed text-faint">
              粉丝自发社区，与腾讯 / KPL / 俱乐部无隶属关系。AI 内容统一标注「AI
              生成」。举报邮箱：report@example.com（上线前替换）。
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
