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
        { role: "assistant", content: "Welcome to **Policyanalyzer**. I am ready to analyze your documents. Please upload your policies in the sidebar to begin." }
    ]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [alerts, setAlerts] = useState<string[]>([]);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(scrollToBottom, [messages]);

    useEffect(() => {
        const handleTriggerComparison = () => {
            setInput("Please run a full compliance comparison between these two documents.");
            // Wait a bit for input state to update before sending
            setTimeout(() => {
                const btn = document.getElementById("send-btn");
                btn?.click();
            }, 100);
        };
        window.addEventListener('trigger-comparison', handleTriggerComparison);
        return () => window.removeEventListener('trigger-comparison', handleTriggerComparison);
    }, []);

    const sendMessage = async (overrideInput?: string) => {
        const currentInput = overrideInput || input;
        if (!currentInput.trim()) return;

        const userMsg = currentInput;
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
            if (response.alerts) {
                setAlerts(response.alerts);
            }
        } catch (error) {
            setMessages(prev => [...prev, { role: "assistant", content: "I encountered an error. Please ensure the backend server is reachable." }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-[75vh] w-full glass-panel border border-white/10 rounded-3xl shadow-3xl overflow-hidden">
            {/* Header */}
            <div className="bg-white/5 backdrop-blur-md p-5 border-b border-white/5 flex justify-between items-center">
                <div className="flex items-center gap-3">
                    <div className="w-2.5 h-2.5 bg-blue-500 rounded-full animate-pulse shadow-[0_0_10px_rgba(59,130,246,0.5)]" />
                    <h3 className="text-white text-sm font-bold tracking-tight">Active Analysis Session</h3>
                </div>
                <div className="flex gap-3">
                    <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider transition-all ${uploadStatus?.regulatory ? 'bg-blue-500 text-white' : 'bg-white/5 text-slate-500'}`}>
                        {uploadStatus?.regulatory && <span className="w-1 h-1 rounded-full bg-white animate-ping" />}
                        Regulatory
                    </div>
                    <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider transition-all ${uploadStatus?.company ? 'bg-blue-500 text-white' : 'bg-white/5 text-slate-500'}`}>
                        {uploadStatus?.company && <span className="w-1 h-1 rounded-full bg-white animate-ping" />}
                        Company
                    </div>
                </div>
            </div>

            {/* Alerts Banner */}
            {alerts.length > 0 && (
                <div className="bg-red-500/10 border-b border-red-500/20 p-3 flex flex-col gap-2 animate-in slide-in-from-top duration-500">
                    {alerts.map((alert, i) => (
                        <div key={i} className="flex items-center gap-2 text-[10px] font-bold text-red-400 uppercase tracking-widest">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-3 h-3">
                                <path fillRule="evenodd" d="M9.401 3.003c.356-.63 1.242-.63 1.598 0l7.859 13.907c.344.609-.094 1.357-.799 1.357H2.94c-.705 0-1.144-.748-.799-1.357l7.859-13.907zM10.25 10a.75.75 0 011.5 0v2.5a.75.75 0 01-1.5 0V10zm.75 6a.75.75 0 100-1.5.75.75 0 000 1.5z" clipRule="evenodd" />
                            </svg>
                            {alert}
                        </div>
                    ))}
                </div>
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-hide">
                {messages.map((msg, idx) => (
                    <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                        <div className={`max-w-[80%] rounded-2xl px-6 py-4 shadow-xl ${msg.role === "user"
                            ? "bg-blue-600 text-white rounded-tr-none"
                            : "bg-white/5 text-slate-100 border border-white/10 rounded-tl-none backdrop-blur-sm"
                            }`}>
                            {msg.role === "assistant" ? (
                                <div className="space-y-4">
                                    <div className="prose prose-invert prose-sm max-w-none
                                        prose-headings:text-white prose-headings:font-bold prose-headings:tracking-tight
                                        prose-p:text-slate-300 prose-p:leading-relaxed
                                        prose-strong:text-blue-400
                                        prose-table:border-white/10
                                        prose-th:bg-blue-900/20 prose-td:border-white/5">
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                            {msg.content.replace(/```json[\s\S]*?```/g, "")}
                                        </ReactMarkdown>
                                    </div>

                                    {/* Metrics Display */}
                                    {msg.content.includes("```json") && (
                                        <MetricsView content={msg.content} />
                                    )}
                                </div>
                            ) : (
                                <p className="text-sm leading-relaxed">{msg.content}</p>
                            )}
                        </div>
                    </div>
                ))}
                {loading && (
                    <div className="flex justify-start">
                        <div className="bg-white/5 border border-white/10 rounded-2xl px-6 py-4 rounded-tl-none flex items-center gap-2">
                            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" />
                            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:0.2s]" />
                            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:0.4s]" />
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-6 bg-black/20 border-t border-white/5 backdrop-blur-xl">
                <div className="flex gap-4">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                        placeholder="Type your inquiry here..."
                        className="flex-1 bg-white/5 text-white placeholder-slate-600 border border-white/10 rounded-2xl px-5 py-4 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 transition-all text-sm"
                    />
                    <button
                        id="send-btn"
                        onClick={() => sendMessage()}
                        disabled={loading || !input.trim()}
                        className="bg-blue-600 hover:bg-blue-500 disabled:bg-white/5 disabled:text-slate-700 text-white px-6 rounded-2xl transition-all hover:scale-105 active:scale-95 shadow-xl shadow-blue-500/20"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="w-5 h-5">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    );
}

function MetricsView({ content }: { content: string }) {
    try {
        const jsonMatch = content.match(/```json([\s\S]*?)```/);
        if (!jsonMatch) return null;
        const data = JSON.parse(jsonMatch[1]);

        return (
            <div className="mt-4 p-5 bg-blue-900/10 border border-blue-500/20 rounded-2xl space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
                <div className="grid grid-cols-3 gap-4">
                    <div className="text-center p-3 bg-black/40 rounded-xl border border-white/5">
                        <div className="text-[10px] text-slate-500 uppercase font-bold mb-1">Compliance</div>
                        <div className="text-2xl font-black text-blue-400">{data.compliance_score}%</div>
                    </div>
                    <div className="text-center p-3 bg-black/40 rounded-xl border border-white/5">
                        <div className="text-[10px] text-slate-500 uppercase font-bold mb-1">Risk Level</div>
                        <div className={`text-sm font-bold mt-2 py-1 px-2 rounded-lg ${data.risk_score === "High" ? "bg-red-500/20 text-red-400" :
                            data.risk_score === "Medium" ? "bg-amber-500/20 text-amber-400" : "bg-green-500/20 text-green-400"
                            }`}>{data.risk_score}</div>
                    </div>
                    <div className="text-center p-3 bg-black/40 rounded-xl border border-white/5">
                        <div className="text-[10px] text-slate-500 uppercase font-bold mb-1">Coverage</div>
                        <div className="text-2xl font-black text-blue-400">{data.coverage_score}</div>
                    </div>
                </div>

                {data.table && (
                    <div className="overflow-hidden rounded-xl border border-white/5 bg-black/20">
                        <table className="w-full text-[11px] text-left">
                            <thead className="bg-white/5 text-slate-400 uppercase font-bold">
                                <tr>
                                    <th className="p-3">Regulation</th>
                                    <th className="p-3">Coverage</th>
                                    <th className="p-3">Risk</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                                {data.table.map((row: any, i: number) => (
                                    <tr key={i} className="hover:bg-white/5 transition-colors">
                                        <td className="p-3 font-semibold text-slate-200">{row.Regulation}</td>
                                        <td className="p-3 text-blue-400 font-bold">{row.Coverage}</td>
                                        <td className="p-3">
                                            <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${row.Risk === "High" ? "bg-red-500/20 text-red-400 border border-red-500/20" :
                                                row.Risk === "Medium" ? "bg-amber-500/20 text-amber-400 border border-amber-500/20" :
                                                    "bg-green-500/20 text-green-400 border border-green-500/20"
                                                }`}>{row.Risk}</span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        );
    } catch (e) {
        return null;
    }
}
