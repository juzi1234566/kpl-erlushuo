/**
 * 手绘橄榄枝花线：图版分隔装饰。
 * 自带边缘颤动与颜料斑驳滤镜，零外部依赖。
 */
export default function Ornament({ className = "" }: { className?: string }) {
  const uid = "花线";
  return (
    <svg
      viewBox="0 0 360 36"
      className={className}
      style={{ width: 220, maxWidth: "60%", height: "auto", display: "block" }}
      aria-hidden
    >
      <defs>
        <filter id={`${uid}-颤`} x="-20%" y="-40%" width="140%" height="180%">
          <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="3" seed="7" result="n" />
          <feDisplacementMap in="SourceGraphic" in2="n" scale="2.5" />
        </filter>
        <linearGradient id={`${uid}-叶`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#7d8c5a" />
          <stop offset="100%" stopColor="#5c6b42" />
        </linearGradient>
      </defs>
      <g filter={`url(#${uid}-颤)`}>
        {/* 两侧细线 */}
        <path d="M4,18 L118,18" stroke="#6b5f3e" strokeWidth="1" opacity="0.55" />
        <path d="M242,18 L356,18" stroke="#6b5f3e" strokeWidth="1" opacity="0.55" />
        {/* 中央橄榄枝 */}
        <path
          d="M132,18 C152,14 200,14 228,18"
          stroke="#5c6b42"
          strokeWidth="1.4"
          fill="none"
          opacity="0.8"
        />
        {[
          { x: 146, r: -32 },
          { x: 162, r: 28 },
          { x: 178, r: -30 },
          { x: 196, r: 30 },
          { x: 212, r: -26 },
        ].map((leaf) => (
          <ellipse
            key={leaf.x}
            cx={leaf.x}
            cy={18}
            rx="9"
            ry="3.4"
            transform={`rotate(${leaf.r} ${leaf.x} 18)`}
            fill={`url(#${uid}-叶)`}
            opacity="0.85"
          />
        ))}
        <circle cx="230" cy="17" r="2.6" fill="#8c6a3c" opacity="0.8" />
        <circle cx="128" cy="19" r="2.6" fill="#8c6a3c" opacity="0.8" />
      </g>
    </svg>
  );
}
