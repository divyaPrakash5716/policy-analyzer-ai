const API_URL = "http://localhost:8000";

export async function uploadDocuments(
    regulatoryDoc: File | null,
    companyPolicy: File | null
) {
    const formData = new FormData();
    if (regulatoryDoc) formData.append("regulatory_doc", regulatoryDoc);
    if (companyPolicy) formData.append("company_policy", companyPolicy);

    const response = await fetch(`${API_URL}/upload`, {
        method: "POST",
        body: formData,
    });

    if (!response.ok) {
        throw new Error("Upload failed");
    }
    return response.json();
}

export async function chatWithAgent(
    message: string,
    policyType: "regulatory" | "company" | "both" | "web"
) {
    const formData = new FormData();
    formData.append("message", message);
    formData.append("policy_type", policyType);

    const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        body: formData,
    });

    if (!response.ok) {
        throw new Error("Chat failed");
    }
    return response.json();
}
