import { ImageResponse } from "next/og";
import { NextRequest } from "next/server";

export const runtime = "edge";

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const title = searchParams.get("title") || "今日串点";
  const body = searchParams.get("body") || "AI 生成的 KPL 玩梗卡片";
  const watermark = "梗局 · AI 生成 · 非官方";

  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: "linear-gradient(145deg, #120f24 0%, #0b0d12 45%, #0d241f 100%)",
          color: "#e8eaf0",
          padding: 48,
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontSize: 28, fontWeight: 700 }}>
            <span style={{ color: "#7c5cff" }}>梗</span>局
          </div>
          <div
            style={{
              fontSize: 16,
              color: "#7c5cff",
              border: "1px solid #7c5cff",
              borderRadius: 999,
              padding: "6px 14px",
            }}
          >
            AI 生成
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ fontSize: 52, fontWeight: 800, lineHeight: 1.15 }}>{title}</div>
          <div style={{ fontSize: 28, color: "#b7bdd0", lineHeight: 1.4, maxWidth: 900 }}>
            {body.slice(0, 120)}
          </div>
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: 18,
            color: "#8b93a7",
          }}
        >
          <span>{watermark}</span>
          <span>fans meme community</span>
        </div>
      </div>
    ),
    { width: 1200, height: 630 }
  );
}
