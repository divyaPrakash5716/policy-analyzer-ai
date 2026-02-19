"use client";

import { useState } from "react";
import UploadSection from "@/components/UploadSection";
import ChatInterface from "@/components/ChatInterface";

interface UploadStatus {
  [key: string]: string | boolean | number;
}

export default function Home() {
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>({});

  return (
    <main className="flex min-h-screen text-white">
      {/* Sidebar - Policy Initializer */}
      <aside className="w-80 sidebar-glass fixed inset-y-0 left-0 z-20 flex flex-col p-6 overflow-y-auto">
        <div className="mb-10">
          <h1 className="text-3xl font-black tracking-tighter text-white">
            Policy<span className="text-blue-500 underline decoration-blue-500/30 underline-offset-4">analyzer</span>
          </h1>
          <p className="text-[10px] text-slate-500 font-bold uppercase tracking-[0.2em] mt-2">
            AI Compliance Engine v2.0
          </p>
        </div>

        <div className="flex-1">
          <UploadSection onUploadComplete={(status) => setUploadStatus((prev) => ({ ...prev, ...status }))} />
        </div>

        <div className="mt-auto pt-6 border-t border-white/5">
          <div className="flex items-center gap-3 p-3 rounded-xl bg-blue-500/5 border border-blue-500/10">
            <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
            <span className="text-[10px] font-semibold text-blue-400 uppercase tracking-widest">System Active</span>
          </div>
        </div>
      </aside>

      {/* Main Content - Chat Interface */}
      <div className="flex-1 ml-80 relative min-h-screen flex flex-col items-center justify-center p-4">
        <div className="w-full max-w-5xl z-10">
          <ChatInterface uploadStatus={uploadStatus} />
        </div>

        <footer className="absolute bottom-6 text-[10px] text-slate-600 font-medium uppercase tracking-widest">
          Powered by FastAPI • LangGraph • Next.js
        </footer>
      </div>
    </main>
  );
}
