/**
 * 手绘枝叶花线：分隔装饰。
 * 自带边缘颤动滤镜，零外部依赖。
 */
export default function Ornament({ className = "" }: { className?: string }) {
  const uid = "orn";
  return (
    <svg
      viewBox="0 0 360 36"
      className={className}
      style={{ width: 220, maxWidth: "60%", height: "auto", display: "block" }}
      aria-hidden
    >
      <defs>
        <filter id={`${uid}-r`} x="-20%" y="-40%" width="140%" height="180%">
          <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="3" seed="7" result="n" />
          <feDisplacementMap in="SourceGraphic" in2="n" scale="2.5" />
        </filter>
        <linearGradient id={`${uid}-l`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#4e8a87" />
          <stop offset="100%" stopColor="#2f6663" />
        </linearGradient>
      </defs>
      <g filter={`url(#${uid}-r)`}>
        {/* 两侧细线 */}
        <path d="M4,18 L118,18" stroke="#3d6a68" strokeWidth="1" opacity="0.5" />
        <path d="M242,18 L356,18" stroke="#3d6a68" strokeWidth="1" opacity="0.5" />
        {/* 中央枝叶 */}
        <path
          d="M132,18 C152,14 200,14 228,18"
          stroke="#2f6663"
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
            fill={`url(#${uid}-l)`}
            opacity="0.85"
          />
        ))}
        <circle cx="230" cy="17" r="2.6" fill="#3d7a77" opacity="0.8" />
        <circle cx="128" cy="19" r="2.6" fill="#3d7a77" opacity="0.8" />
      </g>
    </svg>
  );
}
