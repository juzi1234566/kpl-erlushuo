import { ImageResponse } from "next/og";
import { NextRequest } from "next/server";

export const runtime = "edge";

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const text = searchParams.get("text") || "这场比赛有点东西";
  const caster = searchParams.get("caster") || "二路解说";
  const match = searchParams.get("match") || "";

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
              padding: "44px 60px",
            }}
          >
            {/* 顶部 */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", alignItems: "baseline", gap: 18 }}>
                <div style={{ fontSize: 30, letterSpacing: 14, color: "#263433" }}>梗局</div>
                <div style={{ fontSize: 16, letterSpacing: 4, color: "#64797a" }}>金句时刻</div>
              </div>
              <div
                style={{
                  fontSize: 16,
                  letterSpacing: 3,
                  color: "#a04c34",
                  border: "2px solid rgba(160,76,52,0.65)",
                  padding: "5px 13px",
                  transform: "rotate(-3deg)",
                  background: "rgba(160,76,52,0.06)",
                }}
              >
                AI 摘录
              </div>
            </div>

            {/* 金句主体 */}
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              <div style={{ fontSize: 70, color: "rgba(47,122,125,0.5)", lineHeight: 1 }}>「</div>
              <div
                style={{
                  fontSize: text.length > 40 ? 40 : 52,
                  letterSpacing: 3,
                  lineHeight: 1.5,
                  color: "#263433",
                  maxWidth: 980,
                }}
              >
                {text.slice(0, 80)}
              </div>
              <div
                style={{
                  fontSize: 70,
                  color: "rgba(47,122,125,0.5)",
                  lineHeight: 1,
                  alignSelf: "flex-end",
                }}
              >
                」
              </div>
            </div>

            {/* 落款 */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: 17,
                letterSpacing: 4,
                color: "#2f7a7d",
              }}
            >
              <span>—— {caster}</span>
              <span style={{ color: "#64797a" }}>{match || "王者荣耀职业赛事 · 二路解说"}</span>
            </div>
          </div>
        </div>
      </div>
    ),
    { width: 1200, height: 630 }
  );
}
