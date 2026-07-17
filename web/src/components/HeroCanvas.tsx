"use client";

import { useEffect, useRef } from "react";

/**
 * 首页氛围层：青色尘埃粒子缓慢漂移 + 中央呼吸辉光。
 * additive 混合模拟 bloom；鼠标视差经阻尼，永不瞬移。
 */
export default function HeroCanvas() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let w = 0;
    let h = 0;
    let raf = 0;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      w = rect.width;
      h = rect.height;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();

    const isMobile = w < 768;
    const COUNT = isMobile ? 55 : 110;
    const particles = Array.from({ length: COUNT }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      z: 0.3 + Math.random() * 0.7, // 深度：影响大小/亮度/视差
      vx: (Math.random() - 0.5) * 0.08,
      vy: (Math.random() - 0.5) * 0.05,
      phase: Math.random() * Math.PI * 2,
    }));

    // 阻尼视差
    let tx = 0;
    let ty = 0;
    let px = 0;
    let py = 0;
    const onMove = (e: PointerEvent) => {
      tx = (e.clientX / window.innerWidth - 0.5) * 2;
      ty = (e.clientY / window.innerHeight - 0.5) * 2;
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("resize", resize);

    let t = 0;
    const draw = () => {
      t += 1 / 60;
      px += (tx - px) * 0.04;
      py += (ty - py) * 0.04;

      ctx.clearRect(0, 0, w, h);
      ctx.globalCompositeOperation = "lighter";

      // 中央呼吸辉光（模拟 bloom 主光源）
      const breathe = 0.75 + 0.25 * Math.sin(t * 0.35);
      const gx = w * 0.5 + px * 18;
      const gy = h * 0.44 + py * 12;
      const glow = ctx.createRadialGradient(gx, gy, 0, gx, gy, Math.min(w, h) * 0.55);
      glow.addColorStop(0, `rgba(77, 216, 255, ${0.05 * breathe})`);
      glow.addColorStop(0.5, `rgba(77, 216, 255, ${0.018 * breathe})`);
      glow.addColorStop(1, "rgba(77, 216, 255, 0)");
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, w, h);

      // 尘埃粒子
      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < -10) p.x = w + 10;
        if (p.x > w + 10) p.x = -10;
        if (p.y < -10) p.y = h + 10;
        if (p.y > h + 10) p.y = -10;

        const flicker = 0.6 + 0.4 * Math.sin(t * 0.6 + p.phase);
        const alpha = 0.28 * p.z * flicker;
        const r = 1.1 * p.z + 0.3;
        const ox = px * 26 * p.z;
        const oy = py * 16 * p.z;

        const g = ctx.createRadialGradient(p.x + ox, p.y + oy, 0, p.x + ox, p.y + oy, r * 4);
        g.addColorStop(0, `rgba(150, 230, 255, ${alpha})`);
        g.addColorStop(1, "rgba(150, 230, 255, 0)");
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(p.x + ox, p.y + oy, r * 4, 0, Math.PI * 2);
        ctx.fill();
      }

      ctx.globalCompositeOperation = "source-over";
      raf = requestAnimationFrame(draw);
    };

    if (reduced) {
      // 静态一帧
      t = 10;
      draw();
      cancelAnimationFrame(raf);
    } else {
      raf = requestAnimationFrame(draw);
    }

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={ref}
      aria-hidden
      className="absolute inset-0 h-full w-full"
      style={{ opacity: 0.9 }}
    />
  );
}
