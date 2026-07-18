"use client";

import { useState } from "react";
import { getSupabase } from "@/lib/supabase";

/** 悬浮反馈入口：随时写下不满意的地方，直达站长 */
export default function FeedbackWidget() {
  const [open, setOpen] = useState(false);
  const [content, setContent] = useState("");
  const [contact, setContact] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "done" | "error">("idle");

  async function submit() {
    if (!content.trim()) return;
    setState("sending");
    try {
      const sb = getSupabase();
      if (!sb) throw new Error("no supabase");
      const { error } = await sb.from("feedback").insert({
        content: content.trim().slice(0, 2000),
        contact: contact.trim().slice(0, 200) || null,
        page: typeof window !== "undefined" ? window.location.pathname : null,
      });
      if (error) throw error;
      setState("done");
      setContent("");
      setContact("");
    } catch {
      setState("error");
    }
  }

  return (
    <>
      {/* 悬浮按钮 */}
      <button
        type="button"
        onClick={() => {
          setOpen(!open);
          setState("idle");
        }}
        className="fixed bottom-6 right-6 z-40 border border-border bg-background/95 px-4 py-2.5 text-sm tracking-widest shadow-sm transition-colors duration-300 hover:bg-[rgba(47,122,125,0.08)]"
        aria-label="意见反馈"
      >
        反馈
      </button>

      {/* 面板 */}
      {open && (
        <div className="plate fixed bottom-20 right-6 z-40 w-[min(92vw,360px)] bg-background p-5 shadow-lg">
          {state === "done" ? (
            <div className="py-4 text-center">
              <p className="mb-2 text-[15px] font-medium">收到，谢谢！</p>
              <p className="text-sm text-muted">每条反馈都会看，改进后你会在网站上看到变化。</p>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="btn-plate mt-4"
              >
                关闭
              </button>
            </div>
          ) : (
            <>
              <p className="tag tag--accent mb-3">意见反馈</p>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="哪里不好用、想要什么功能、内容哪里不对……直说，马上改"
                rows={4}
                maxLength={2000}
                className="mb-2 w-full resize-none border border-border bg-transparent p-3 text-sm leading-relaxed outline-none placeholder:text-faint focus:border-accent/60"
              />
              <input
                value={contact}
                onChange={(e) => setContact(e.target.value)}
                placeholder="联系方式（选填，方便回复你）"
                maxLength={200}
                className="mb-3 w-full border border-border bg-transparent px-3 py-2 text-sm outline-none placeholder:text-faint focus:border-accent/60"
              />
              {state === "error" && (
                <p className="mb-2 text-xs text-seal">
                  提交失败了，可以直接发邮件到 report@example.com
                </p>
              )}
              <div className="flex justify-end gap-3">
                <button type="button" onClick={() => setOpen(false)} className="tag hover:text-foreground">
                  取消
                </button>
                <button
                  type="button"
                  onClick={submit}
                  disabled={state === "sending" || !content.trim()}
                  className="btn-plate btn-plate--primary disabled:opacity-50"
                >
                  {state === "sending" ? "提交中…" : "提交"}
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </>
  );
}
