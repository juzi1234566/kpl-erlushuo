import { ImageResponse } from "next/og";
import { NextRequest } from "next/server";

export const runtime = "edge";

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const title = searchParams.get("title") || "今日串点";
  const body = searchParams.get("body") || "AI 生成的 KPL 玩梗卡片";

  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background:
            "radial-gradient(900px 450px at 50% -15%, rgba(77,216,255,0.12), transparent 60%), #05060a",
          color: "rgba(235,240,248,0.92)",
          padding: 56,
          fontFamily: "sans-serif",
        }}
      >
        {/* 顶部 HUD */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div style={{ display: "flex", alignItems: "baseline", gap: 16 }}>
            <div style={{ fontSize: 30, fontWeight: 300, letterSpacing: 8 }}>
              <span style={{ color: "#4dd8ff" }}>梗</span>局
            </div>
            <div
              style={{
                fontSize: 13,
                letterSpacing: 5,
                color: "rgba(235,240,248,0.3)",
                textTransform: "uppercase",
              }}
            >
              Unofficial · Fan Community
            </div>
          </div>
          <div
            style={{
              fontSize: 14,
              letterSpacing: 4,
              textTransform: "uppercase",
              color: "rgba(138,107,255,0.9)",
              border: "1px solid rgba(138,107,255,0.4)",
              borderRadius: 4,
              padding: "8px 18px",
            }}
          >
            AI 生成
          </div>
        </div>

        {/* 主体 */}
        <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
          <div
            style={{
              fontSize: 60,
              fontWeight: 300,
              letterSpacing: 4,
              lineHeight: 1.2,
              color: "#eef4fa",
            }}
          >
            {title}
          </div>
          <div
            style={{
              fontSize: 26,
              fontWeight: 300,
              color: "rgba(235,240,248,0.5)",
              lineHeight: 1.55,
              maxWidth: 920,
            }}
          >
            {body.slice(0, 120)}
          </div>
        </div>

        {/* 底部 HUD */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            fontSize: 14,
            letterSpacing: 4,
            textTransform: "uppercase",
            color: "rgba(235,240,248,0.28)",
          }}
        >
          <span>梗局 · AI Generated · 非官方</span>
          <span style={{ color: "rgba(77,216,255,0.6)" }}>KPL-MEME</span>
        </div>
      </div>
    ),
    { width: 1200, height: 630 }
  );
}
