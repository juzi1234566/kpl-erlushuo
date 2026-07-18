import Link from "next/link";
import type { RatingTable } from "@/lib/consensus";

function Cell({ rating, sentiment }: { rating: number | null; sentiment: string }) {
  const color =
    sentiment === "好评" ? "text-accent" : sentiment === "差评" ? "text-seal" : "text-muted";
  return (
    <span className={`font-medium ${color}`}>
      {rating ? `★${rating}` : sentiment || "—"}
    </span>
  );
}

function VerdictTag({ verdict }: { verdict: string }) {
  if (verdict === "褒贬不一") return <span className="seal-ai">{verdict}</span>;
  if (verdict === "一致好评" || verdict === "偏好评")
    return <span className="tag tag--accent">{verdict}</span>;
  if (verdict === "一致差评" || verdict === "偏差评")
    return <span className="tag text-seal">{verdict}</span>;
  return <span className="tag">{verdict}</span>;
}

/** 解说团打分表：行=战队/选手，列=各解说星级，末列一句总体评价 */
export default function ConsensusBar({ table }: { table: RatingTable }) {
  if (!table.rows.length) return null;
  return (
    <div className="plate p-5 md:p-6">
      <p className="tag tag--accent mb-4">解说团打分表</p>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[480px] text-[15px]">
          <thead>
            <tr className="border-b border-border/50">
              <th className="tag py-2 pr-4 text-left font-normal">对象</th>
              {table.casters.map((c) => (
                <th key={c} className="tag px-3 py-2 text-center font-normal">
                  {c}
                </th>
              ))}
              <th className="tag py-2 pl-3 text-left font-normal">总体评价</th>
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row) => (
              <tr
                key={`${row.subject_type}-${row.subject_name}`}
                className="border-b border-border/25 last:border-b-0"
              >
                <td className="py-2.5 pr-4">
                  {row.subject_type === "player" ? (
                    <Link
                      href={`/players/${encodeURIComponent(row.subject_name)}`}
                      className="font-semibold underline-offset-4 hover:underline"
                    >
                      {row.subject_name}
                    </Link>
                  ) : (
                    <span className="font-semibold">{row.subject_name}</span>
                  )}
                </td>
                {table.casters.map((c) => (
                  <td key={c} className="px-3 py-2.5 text-center">
                    {row.cells[c] ? (
                      <Cell rating={row.cells[c].rating} sentiment={row.cells[c].sentiment} />
                    ) : (
                      <span className="text-faint">—</span>
                    )}
                  </td>
                ))}
                <td className="py-2.5 pl-3">
                  <VerdictTag verdict={row.verdict} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
