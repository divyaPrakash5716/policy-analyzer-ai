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
    <main className="min-h-screen bg-slate-900 bg-[radial-gradient(ellipse_at_top,var(--tw-gradient-stops))] from-slate-900 via-[#1a1c2e] to-black text-white selection:bg-purple-500/30">
      {/* Animated Background Elements */}
      <div className="fixed top-0 left-0 w-full h-full overflow-hidden z-0 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-purple-600/20 rounded-full blur-[120px] animate-pulse" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-600/20 rounded-full blur-[120px] animate-pulse [animation-delay:2s]" />
      </div>

      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen p-4 md:p-8">
        <header className="mb-12 text-center space-y-4">
          <h1 className="text-5xl md:text-7xl font-extrabold text-transparent bg-clip-text bg-linear-to-r from-blue-400 via-purple-400 to-pink-400 tracking-tight drop-shadow-2xl">
            Policy Analyser AI
          </h1>
          <p className="text-lg md:text-xl text-gray-400 max-w-2xl mx-auto font-light">
            Agentic RAG System powered by advanced LLMs to analyze, compare, and verify regulatory compliance.
          </p>
        </header>

        <UploadSection onUploadComplete={(status) => setUploadStatus((prev) => ({ ...prev, ...status }))} />

        <div className="w-full mt-8">
          <ChatInterface uploadStatus={uploadStatus} />
        </div>

        <footer className="mt-16 text-gray-600 text-sm">
          Built with FastAPI, LangGraph, & Next.js
        </footer>
      </div>
    </main>
  );
}
