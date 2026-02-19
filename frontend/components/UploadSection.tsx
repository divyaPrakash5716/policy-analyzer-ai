"use client";

import { useState } from "react";

export default function UploadSection({ onUploadComplete }: { onUploadComplete: (status: any) => void }) {
    const [regulatoryDoc, setRegulatoryDoc] = useState<File | null>(null);
    const [companyPolicy, setCompanyPolicy] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>, type: "regulatory" | "company") => {
        if (e.target.files && e.target.files[0]) {
            if (type === "regulatory") setRegulatoryDoc(e.target.files[0]);
            else setCompanyPolicy(e.target.files[0]);
        }
    };

    const handleUpload = async () => {
        if (!regulatoryDoc && !companyPolicy) return;
        setUploading(true);
        try {
            const { uploadDocuments } = await import("@/lib/api");
            const result = await uploadDocuments(regulatoryDoc, companyPolicy);
            onUploadComplete(result.status);

            // Check for dual upload and offer comparison
            if (regulatoryDoc && companyPolicy) {
                if (confirm("Both documents uploaded successfully! Would you like to automatically run a compliance comparison now?")) {
                    // This logic will be handled by the parent or by sending a specific message
                    window.dispatchEvent(new CustomEvent('trigger-comparison'));
                }
            }
        } catch (error) {
            console.error(error);
            alert("Upload failed");
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="flex flex-col gap-8 w-full">
            <div className="space-y-6">
                <div className="p-4 rounded-xl bg-blue-900/10 border border-blue-500/20">
                    <label className="block text-xs font-bold text-blue-400 uppercase tracking-wider mb-3">Regulatory Policy</label>
                    <input
                        type="file"
                        onChange={(e) => handleFileChange(e, "regulatory")}
                        className="block w-full text-xs text-slate-400
                            file:mr-3 file:py-2 file:px-4
                            file:rounded-lg file:border-0
                            file:text-xs file:font-semibold
                            file:bg-slate-800 file:text-white
                            hover:file:bg-slate-700
                            cursor-pointer bg-black/40 rounded-lg border border-slate-700 focus:outline-none focus:border-blue-500 transition-all"
                    />
                    {regulatoryDoc && <p className="mt-2 text-[10px] text-blue-300 truncate">Selected: {regulatoryDoc.name}</p>}
                </div>

                <div className="p-4 rounded-xl bg-blue-900/10 border border-blue-500/20">
                    <label className="block text-xs font-bold text-blue-400 uppercase tracking-wider mb-3">Company Policy</label>
                    <input
                        type="file"
                        onChange={(e) => handleFileChange(e, "company")}
                        className="block w-full text-xs text-slate-400
                            file:mr-3 file:py-2 file:px-4
                            file:rounded-lg file:border-0
                            file:text-xs file:font-semibold
                            file:bg-blue-600 file:text-white
                            hover:file:bg-blue-700
                            cursor-pointer bg-black/40 rounded-lg border border-slate-700 focus:outline-none focus:border-blue-500 transition-all"
                    />
                    {companyPolicy && <p className="mt-2 text-[10px] text-blue-300 truncate">Selected: {companyPolicy.name}</p>}
                </div>
            </div>

            <button
                onClick={handleUpload}
                disabled={uploading || (!regulatoryDoc && !companyPolicy)}
                className={`w-full py-4 rounded-xl font-bold text-sm tracking-wide shadow-xl transition-all active:scale-[0.98]
                    ${uploading
                        ? "bg-slate-800 text-slate-500 cursor-not-allowed"
                        : "bg-gradient-to-r from-blue-700 to-blue-500 hover:from-blue-600 hover:to-blue-400 text-white shadow-blue-900/20"
                    }`}
            >
                {uploading ? (
                    <span className="flex items-center justify-center gap-2">
                        <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        Analyzing...
                    </span>
                ) : "Initialize Context"}
            </button>
        </div>
    );
}
