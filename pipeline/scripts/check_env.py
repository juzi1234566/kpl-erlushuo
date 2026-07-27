"""检查本机环境是否齐活（不打印密钥内容）。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def mask(v: str | None) -> str:
    if not v:
        return "❌ 缺失"
    if len(v) <= 8:
        return f"✅ 已设置 (len={len(v)})"
    return f"✅ 已设置 (len={len(v)}, head={v[:4]}…)"


def main() -> None:
    print("pipeline/.env")
    print("  DEEPSEEK_API_KEY     ", mask(os.getenv("DEEPSEEK_API_KEY")))
    print("  DEEPSEEK_BASE_URL    ", os.getenv("DEEPSEEK_BASE_URL") or "(default)")
    print("  DEEPSEEK_MODEL       ", os.getenv("DEEPSEEK_MODEL") or "(default)")
    print("  SUPABASE_URL         ", mask(os.getenv("SUPABASE_URL")))
    print("  SUPABASE_SERVICE_ROLE", mask(os.getenv("SUPABASE_SERVICE_ROLE_KEY")))

    web_env = ROOT.parent / "web" / ".env.local"
    print("web/.env.local", "存在" if web_env.exists() else "❌ 不存在")
    if web_env.exists():
        # parse without dotenv pollution
        data = {}
        for line in web_env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                data[k.strip()] = v.strip()
        print("  NEXT_PUBLIC_SUPABASE_URL     ", mask(data.get("NEXT_PUBLIC_SUPABASE_URL")))
        print("  NEXT_PUBLIC_SUPABASE_ANON_KEY", mask(data.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")))

    missing = []
    if not os.getenv("DEEPSEEK_API_KEY"):
        missing.append("DEEPSEEK_API_KEY")
    if not os.getenv("SUPABASE_URL"):
        missing.append("SUPABASE_URL")
    if not os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    if missing:
        print("\n还缺:", ", ".join(missing))
        print("把缺的项填进 pipeline/.env 后重跑: python -m scripts.check_env")
        sys.exit(1)
    print("\n环境检查通过")


if __name__ == "__main__":
    main()
