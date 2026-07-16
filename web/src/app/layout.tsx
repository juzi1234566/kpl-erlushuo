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

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <header className="border-b border-border/80 backdrop-blur sticky top-0 z-20 bg-background/70">
          <div className="mx-auto max-w-5xl px-4 h-14 flex items-center justify-between">
            <Link href="/" className="font-semibold tracking-wide">
              <span className="text-accent">梗</span>局
              <span className="ml-2 text-xs text-muted font-normal">非官方粉丝社区</span>
            </Link>
            <nav className="flex gap-4 text-sm text-muted">
              <Link href="/memes" className="hover:text-foreground">
                梗百科
              </Link>
              <Link href="/matches" className="hover:text-foreground">
                赛程
              </Link>
              <Link href="/about" className="hover:text-foreground">
                关于
              </Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-4 py-8">{children}</main>
        <footer className="border-t border-border/80 mt-16">
          <div className="mx-auto max-w-5xl px-4 py-8 text-xs text-muted space-y-2">
            <p>梗局是粉丝自发社区，与腾讯 / KPL / 俱乐部无隶属关系。</p>
            <p>
              AI 内容统一标注「AI 生成」。举报邮箱：report@example.com（上线前替换）。
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
