"use client";

import { useEffect, useRef } from "react";

/** 胶片颗粒：低帧率换 turbulence seed，像老放映机（尊重减少动效偏好） */
export default function GrainOverlay() {
  const ref = useRef<SVGFETurbulenceElement>(null);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const id = setInterval(() => {
      ref.current?.setAttribute("seed", String(Math.floor(Math.random() * 1000)));
    }, 140);
    return () => clearInterval(id);
  }, []);

  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 z-40"
      style={{ opacity: 0.045, mixBlendMode: "multiply" }}
    >
      <svg width="100%" height="100%">
        <filter id="颗粒滤镜">
          <feTurbulence ref={ref} type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="1" />
          <feColorMatrix
            type="matrix"
            values="0 0 0 0 0.22  0 0 0 0 0.18  0 0 0 0 0.10  0 0 0 0.6 0"
          />
        </filter>
        <rect width="100%" height="100%" filter="url(#颗粒滤镜)" />
      </svg>
    </div>
  );
}
