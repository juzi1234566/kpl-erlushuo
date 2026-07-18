import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 关闭开发模式左下角的 Next.js 调试角标（仅本地开发可见，生产本来就没有）
  devIndicators: false,
};

export default nextConfig;
