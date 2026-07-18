import Link from "next/link";
import type { ConsensusItem } from "@/lib/consensus";

const KIND_STYLE: Record<ConsensusItem["kind"], string> = {
  两极分化: "seal-ai",
  共识差评: "tag text-seal",
  共识好评: "tag tag--accent",
};

/** 比赛页顶部：跨主播的共识与分歧一览（入口级爆点） */
export default function ConsensusBar({ items }: { items: ConsensusItem[] }) {
  if (!items.length) return null;
  return (
    <div className="plate p-5 md:p-6">
      <p className="tag tag--accent mb-4">解说团意见速览</p>
      <div className="space-y-2.5">
        {items.map((c) => (
          <div key={`${c.subject_type}-${c.subject_name}`} className="flex flex-wrap items-baseline gap-2.5 text-[15px]">
            <span className={KIND_STYLE[c.kind]}>{c.kind}</span>
            {c.subject_type === "player" ? (
              <Link
                href={`/players/${encodeURIComponent(c.subject_name)}`}
                className="font-semibold tracking-wide underline-offset-4 hover:underline"
              >
                {c.subject_name}
              </Link>
            ) : (
              <span className="font-semibold tracking-wide">{c.subject_name}</span>
            )}
            <span className="text-sm text-muted">{c.detail}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
