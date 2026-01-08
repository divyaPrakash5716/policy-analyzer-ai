"use client";

import { useState, useCallback } from "react";

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
        } catch (error) {
            console.error(error);
            alert("Upload failed");
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="bg-white/10 backdrop-blur-md border border-white/20 p-6 rounded-2xl shadow-xl w-full max-w-2xl mx-auto my-8">
            <h2 className="text-2xl font-bold text-white mb-6 text-center">Upload Policies</h2>
            <div className="flex flex-col md:flex-row gap-6">
                <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-200 mb-2">Regulatory Policy (PDF/Text)</label>
                    <div className="relative group">
                        <input
                            type="file"
                            onChange={(e) => handleFileChange(e, "regulatory")}
                            className="block w-full text-sm text-gray-400
                file:mr-4 file:py-3 file:px-6
                file:rounded-xl file:border-0
                file:text-sm file:font-semibold
                file:bg-purple-600 file:text-white
                hover:file:bg-purple-700
                cursor-pointer bg-black/20 rounded-xl border border-gray-600 focus:outline-none focus:border-purple-500 transition-all p-1"
                        />
                    </div>
                </div>
                <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-200 mb-2">Company Policy (PDF/Text)</label>
                    <div className="relative group">
                        <input
                            type="file"
                            onChange={(e) => handleFileChange(e, "company")}
                            className="block w-full text-sm text-gray-400
                file:mr-4 file:py-3 file:px-6
                file:rounded-xl file:border-0
                file:text-sm file:font-semibold
                file:bg-blue-600 file:text-white
                hover:file:bg-blue-700
                cursor-pointer bg-black/20 rounded-xl border border-gray-600 focus:outline-none focus:border-blue-500 transition-all p-1"
                        />
                    </div>
                </div>
            </div>

            <div className="mt-8 flex justify-center">
                <button
                    onClick={handleUpload}
                    disabled={uploading || (!regulatoryDoc && !companyPolicy)}
                    className={`px-8 py-3 rounded-xl font-bold text-white shadow-lg transform transition-all hover:scale-105 active:scale-95
              ${uploading
                            ? "bg-gray-500 cursor-not-allowed"
                            : "bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 ring-2 ring-transparent hover:ring-white/20"
                        }`}
                >
                    {uploading ? "Analyzing..." : "Analyze & Ingest"}
                </button>
            </div>
        </div>
    );
}
