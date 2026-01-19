"use client";

import { useState, useRef, useEffect } from "react";
import { chatWithAgent } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Message = {
    role: "user" | "assistant";
    content: string;
};

export default function ChatInterface({ uploadStatus }: { uploadStatus: any }) {
    const [messages, setMessages] = useState<Message[]>([
        { role: "assistant", content: "Hello! I am your Policy Analyser AI. Upload your policies to get started." }
    ]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(scrollToBottom, [messages]);

    const sendMessage = async () => {
        if (!input.trim()) return;

        const userMsg = input;
        setInput("");
        setMessages(prev => [...prev, { role: "user", content: userMsg }]);
        setLoading(true);

        try {
            // Determine policy type based on upload status
            let policyType: "regulatory" | "company" | "both" | "web" = "web";
            if (uploadStatus?.regulatory && uploadStatus?.company) policyType = "both";
            else if (uploadStatus?.company) policyType = "company";

            const response = await chatWithAgent(userMsg, policyType);

            setMessages(prev => [...prev, { role: "assistant", content: response.response }]);
        } catch (error) {
            setMessages(prev => [...prev, { role: "assistant", content: "Sorry, I encountered an error potentially due to connection issues or backend availability." }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-[600px] w-full max-w-4xl mx-auto bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="bg-white/10 p-4 border-b border-white/10 flex justify-between items-center">
                <h3 className="text-white font-semibold">Agentic Chat</h3>
                <div className="flex gap-2">
                    <span className={`px-2 py-1 rounded text-xs ${uploadStatus?.regulatory ? 'bg-green-500/20 text-green-300' : 'bg-gray-500/20 text-gray-400'}`}>Regulatory</span>
                    <span className={`px-2 py-1 rounded text-xs ${uploadStatus?.company ? 'bg-blue-500/20 text-blue-300' : 'bg-gray-500/20 text-gray-400'}`}>Company</span>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
                {messages.map((msg, idx) => (
                    <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                        <div className={`max-w-[80%] rounded-2xl px-6 py-3 shadow-lg ${msg.role === "user"
                            ? "bg-gradient-to-br from-blue-600 to-indigo-600 text-white rounded-tr-none"
                            : "bg-white/10 text-gray-100 border border-white/5 rounded-tl-none"
                            }`}>
                            {msg.role === "assistant" ? (
                                <div className="prose prose-invert prose-sm max-w-none
                                    prose-headings:text-white prose-headings:font-semibold prose-headings:mt-4 prose-headings:mb-2
                                    prose-h1:text-xl prose-h2:text-lg prose-h3:text-base
                                    prose-p:text-gray-200 prose-p:my-2
                                    prose-strong:text-white prose-strong:font-semibold
                                    prose-ul:my-2 prose-ul:pl-4 prose-li:text-gray-200 prose-li:my-1
                                    prose-ol:my-2 prose-ol:pl-4
                                    prose-table:my-3 prose-table:text-sm prose-table:w-full prose-table:border-collapse
                                    prose-th:bg-white/10 prose-th:px-3 prose-th:py-2 prose-th:text-left prose-th:font-semibold prose-th:text-white prose-th:border prose-th:border-white/20
                                    prose-td:px-3 prose-td:py-2 prose-td:border prose-td:border-white/10 prose-td:text-gray-300
                                    prose-code:bg-white/10 prose-code:px-1 prose-code:rounded prose-code:text-blue-300
                                    prose-hr:border-white/20 prose-hr:my-4">
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                                </div>
                            ) : (
                                <p className="whitespace-pre-wrap">{msg.content}</p>
                            )}
                        </div>
                    </div>
                ))}
                {loading && (
                    <div className="flex justify-start">
                        <div className="bg-white/10 rounded-2xl px-6 py-3 rounded-tl-none flex items-center gap-2">
                            <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" />
                            <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce [animation-delay:0.2s]" />
                            <div className="w-2 h-2 bg-pink-400 rounded-full animate-bounce [animation-delay:0.4s]" />
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-4 bg-white/5 border-t border-white/10">
                <div className="flex gap-4">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                        placeholder="Ask about policy discrepancies, compliance, or general questions..."
                        className="flex-1 bg-black/20 text-white placeholder-gray-500 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                    />
                    <button
                        onClick={sendMessage}
                        disabled={loading || !input.trim()}
                        className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 text-white p-3 rounded-xl transition-all hover:scale-105 active:scale-95"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-6 h-6">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    );
}
