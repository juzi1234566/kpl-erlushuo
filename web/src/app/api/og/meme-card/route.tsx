import { ImageResponse } from "next/og";
import { NextRequest } from "next/server";

export const runtime = "edge";

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const title = searchParams.get("title") || "今日串点";
  const body = searchParams.get("body") || "赛后自动整理的玩梗词条";

  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          background:
            "radial-gradient(700px 500px at 20% 15%, rgba(47,122,125,0.10), transparent 65%), radial-gradient(600px 420px at 85% 80%, rgba(47,122,125,0.12), transparent 60%), #e0e9e7",
          padding: 34,
          fontFamily: "serif",
        }}
      >
        {/* 细双线边框 */}
        <div
          style={{
            flex: 1,
            display: "flex",
            border: "1.5px solid rgba(38,74,74,0.5)",
            padding: 7,
          }}
        >
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
              border: "1px solid rgba(38,74,74,0.28)",
              padding: "40px 56px",
            }}
          >
            {/* 顶部 */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div style={{ display: "flex", alignItems: "baseline", gap: 20 }}>
                <div style={{ fontSize: 34, letterSpacing: 16, color: "#263433" }}>梗局</div>
                <div style={{ fontSize: 15, letterSpacing: 6, color: "#64797a" }}>
                  非官方粉丝社区
                </div>
              </div>
              <div
                style={{
                  fontSize: 17,
                  letterSpacing: 3,
                  color: "#a04c34",
                  border: "2px solid rgba(160,76,52,0.65)",
                  padding: "6px 14px",
                  transform: "rotate(-3deg)",
                  background: "rgba(160,76,52,0.06)",
                }}
              >
                AI 生成
              </div>
            </div>

            {/* 主体 */}
            <div style={{ display: "flex", flexDirection: "column", gap: 26 }}>
              <div
                style={{
                  fontSize: 62,
                  letterSpacing: 10,
                  lineHeight: 1.25,
                  color: "#263433",
                }}
              >
                {title}
              </div>
              <div
                style={{
                  fontSize: 26,
                  color: "#46585a",
                  lineHeight: 1.7,
                  maxWidth: 900,
                }}
              >
                {body.slice(0, 110)}
              </div>
            </div>

            {/* 底部 */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: 16,
                letterSpacing: 5,
                color: "#2f7a7d",
              }}
            >
              <span>梗局 · 玩梗社区 · 非官方</span>
              <span>2026 夏</span>
            </div>
          </div>
        </div>
      </div>
    ),
    { width: 1200, height: 630 }
  );
}
