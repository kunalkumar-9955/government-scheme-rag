"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { documentsApi, schemesApi } from "@/lib/api/endpoints";

export default function AdminDocumentsPage() {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [selectedError, setSelectedError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [formData, setFormData] = useState({
    title: "",
    scheme: "",
    ministry: "",
    category: "GUIDELINE",
    document_version: "1.0",
    chunking_strategy: "recursive",
  });

  // Fetch all documents
  const { data: docsRes, isLoading } = useQuery({
    queryKey: ["adminDocumentsList", { status: statusFilter }],
    queryFn: () => documentsApi.listDocuments({ status: statusFilter || undefined }),
    refetchInterval: 10000, // Live poll for status updates
  });

  // Fetch schemes for association
  const { data: schemesRes } = useQuery({
    queryKey: ["adminSchemesForDocs"],
    queryFn: () => schemesApi.listSchemes({ page_size: 100 }),
  });

  const documents = docsRes?.data?.results || [];
  const schemes = schemesRes?.data?.results || [];

  // Upload Mutation
  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!selectedFile) throw new Error("No file selected");
      const form = new FormData();
      form.append("file", selectedFile);
      form.append("title", formData.title || selectedFile.name);
      if (formData.scheme) form.append("scheme", formData.scheme);
      if (formData.ministry) form.append("ministry", formData.ministry);
      form.append("category", formData.category);
      form.append("document_version", formData.document_version);
      form.append("chunking_strategy", formData.chunking_strategy);

      return documentsApi.upload(form);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminDocumentsList"] });
      setSelectedFile(null);
      setFormData({
        title: "",
        scheme: "",
        ministry: "",
        category: "GUIDELINE",
        document_version: "1.0",
        chunking_strategy: "recursive",
      });
    },
  });

  // Reprocess Mutation
  const reprocessMutation = useMutation({
    mutationFn: (docId: string) => documentsApi.reprocessDocument(docId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminDocumentsList"] });
    },
  });

  // Delete Mutation
  const deleteMutation = useMutation({
    mutationFn: (docId: string) => documentsApi.deleteDocument(docId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminDocumentsList"] });
    },
  });

  const handleUpload = (e: React.FormEvent) => {
    e.preventDefault();
    uploadMutation.mutate();
  };

  const filteredDocs = documents.filter((d: any) => {
    if (!searchTerm.trim()) return true;
    const q = searchTerm.toLowerCase();
    return d.title?.toLowerCase().includes(q) || d.file_name?.toLowerCase().includes(q) || d.ministry?.toLowerCase().includes(q);
  });

  return (
    <div style={{ padding: "2rem", height: "100%", overflowY: "auto" }}>
      {/* Header */}
      <div style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "0 0 0.4rem" }}>
          📁 Document Ingestion & Pipeline Management
        </h1>
        <p style={{ color: "var(--color-text-secondary)", fontSize: "0.9rem" }}>
          Upload official PDFs/DOCXs, monitor chunking and vector embedding status, and inspect extraction diagnostics.
        </p>
      </div>

      {/* Upload Box */}
      <div
        className="card-elevated"
        style={{
          padding: "1.5rem",
          borderRadius: "var(--radius-xl)",
          marginBottom: "2rem",
          border: "1px solid var(--color-border)",
        }}
      >
        <h3 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "1rem" }}>
          Upload New Government Document
        </h3>

        <form onSubmit={handleUpload} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.75rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                Document Title *
              </label>
              <input
                type="text"
                placeholder="e.g. PM-KISAN Operational Guidelines 2024"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className="input-field"
                required
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                Associated Scheme (Optional)
              </label>
              <select
                value={formData.scheme}
                onChange={(e) => setFormData({ ...formData, scheme: e.target.value })}
                className="input-field"
              >
                <option value="">Select Scheme</option>
                {schemes.map((s: any) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                Document Category
              </label>
              <select
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                className="input-field"
              >
                <option value="GUIDELINE">Operational Guideline</option>
                <option value="GAZETTE_NOTIFICATION">Gazette Notification</option>
                <option value="APPLICATION_FORM">Application Form / Checklist</option>
                <option value="POLICY_BRIEF">Policy Brief / Circular</option>
                <option value="FAQ">Official FAQs</option>
              </select>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.75rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                Nodal Ministry
              </label>
              <input
                type="text"
                placeholder="e.g. Ministry of Agriculture"
                value={formData.ministry}
                onChange={(e) => setFormData({ ...formData, ministry: e.target.value })}
                className="input-field"
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                Document Version
              </label>
              <input
                type="text"
                placeholder="e.g. 1.0, 2.1"
                value={formData.document_version}
                onChange={(e) => setFormData({ ...formData, document_version: e.target.value })}
                className="input-field"
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                Chunking Strategy
              </label>
              <select
                value={formData.chunking_strategy}
                onChange={(e) => setFormData({ ...formData, chunking_strategy: e.target.value })}
                className="input-field"
              >
                <option value="recursive">Recursive Character (512 tokens)</option>
                <option value="semantic">Semantic Heading Chunking</option>
                <option value="page">Per-Page Preservation</option>
              </select>
            </div>
          </div>

          {/* File Picker */}
          <div style={{ border: "2px dashed var(--color-border)", borderRadius: "var(--radius-md)", padding: "1.25rem", textAlign: "center", background: "var(--color-bg-overlay)" }}>
            <input
              type="file"
              accept=".pdf,.docx,.doc,.txt,.html"
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              style={{ display: "none" }}
              id="file-upload"
              required
            />
            <label htmlFor="file-upload" style={{ cursor: "pointer" }}>
              <span style={{ fontSize: "1.5rem", display: "block", marginBottom: "0.35rem" }}>📄</span>
              <span style={{ fontSize: "0.88rem", fontWeight: 600, color: "var(--color-primary)" }}>
                {selectedFile ? selectedFile.name : "Click to select PDF or DOCX file"}
              </span>
              <p style={{ fontSize: "0.72rem", color: "var(--color-text-muted)", margin: "0.2rem 0 0" }}>
                Supported formats: .pdf, .docx, .html, .txt (Max 50MB)
              </p>
            </label>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button
              type="submit"
              disabled={!selectedFile || uploadMutation.isPending}
              className="btn-primary"
              style={{ padding: "0.6rem 1.25rem" }}
            >
              {uploadMutation.isPending ? "Uploading & Ingesting..." : "Upload & Ingest Document"}
            </button>
          </div>
        </form>
      </div>

      {/* Filter and Search */}
      <div style={{ display: "flex", gap: "1rem", marginBottom: "1.25rem", flexWrap: "wrap" }}>
        <input
          type="text"
          placeholder="🔍 Search documents..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="input-field"
          style={{ maxWidth: "320px" }}
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="input-field"
          style={{ maxWidth: "200px" }}
        >
          <option value="">All Statuses</option>
          <option value="COMPLETED">Completed</option>
          <option value="PROCESSING">Processing</option>
          <option value="PENDING">Pending</option>
          <option value="FAILED">Failed</option>
        </select>
      </div>

      {/* Documents Table */}
      <div className="card-elevated" style={{ borderRadius: "var(--radius-xl)", overflow: "hidden", border: "1px solid var(--color-border)" }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--color-border)", textAlign: "left", background: "var(--color-bg-overlay)", color: "var(--color-text-muted)" }}>
                <th style={{ padding: "0.85rem 1rem" }}>Document Title</th>
                <th style={{ padding: "0.85rem 1rem" }}>File Name</th>
                <th style={{ padding: "0.85rem 1rem" }}>Status</th>
                <th style={{ padding: "0.85rem 1rem" }}>Chunks</th>
                <th style={{ padding: "0.85rem 1rem" }}>Size</th>
                <th style={{ padding: "0.85rem 1rem" }}>Uploaded</th>
                <th style={{ padding: "0.85rem 1rem", textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredDocs.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: "2.5rem", textAlign: "center", color: "var(--color-text-muted)" }}>
                    No documents uploaded yet.
                  </td>
                </tr>
              ) : (
                filteredDocs.map((doc: any) => (
                  <tr key={doc.id} style={{ borderBottom: "1px solid var(--color-border-subtle)" }}>
                    <td style={{ padding: "0.85rem 1rem", fontWeight: 600, color: "var(--color-text-primary)" }}>
                      {doc.title}
                      {doc.ministry && (
                        <div style={{ fontSize: "0.72rem", color: "var(--color-text-muted)", fontWeight: 400 }}>
                          {doc.ministry}
                        </div>
                      )}
                    </td>
                    <td style={{ padding: "0.85rem 1rem", color: "var(--color-text-secondary)" }}>
                      {doc.file_name}
                    </td>
                    <td style={{ padding: "0.85rem 1rem" }}>
                      <span
                        className={`badge ${
                          doc.status === "COMPLETED"
                            ? "badge-success"
                            : doc.status === "FAILED"
                            ? "badge-danger"
                            : "badge-accent"
                        }`}
                      >
                        {doc.status}
                      </span>
                    </td>
                    <td style={{ padding: "0.85rem 1rem", fontWeight: 600 }}>
                      {doc.total_chunks || 0}
                    </td>
                    <td style={{ padding: "0.85rem 1rem", color: "var(--color-text-muted)" }}>
                      {doc.file_size_bytes ? `${(doc.file_size_bytes / 1024).toFixed(0)} KB` : "—"}
                    </td>
                    <td style={{ padding: "0.85rem 1rem", color: "var(--color-text-muted)" }}>
                      {doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : "—"}
                    </td>
                    <td style={{ padding: "0.85rem 1rem", textAlign: "right" }}>
                      <div style={{ display: "flex", gap: "0.4rem", justifyContent: "flex-end" }}>
                        {doc.status === "FAILED" && doc.processing_error && (
                          <button
                            onClick={() => setSelectedError(doc.processing_error)}
                            className="btn-ghost"
                            style={{ fontSize: "0.75rem", padding: "0.25rem 0.5rem", color: "var(--color-danger)" }}
                          >
                            ⚠️ Error
                          </button>
                        )}
                        <button
                          onClick={() => reprocessMutation.mutate(doc.id)}
                          disabled={reprocessMutation.isPending || doc.status === "PROCESSING"}
                          className="btn-secondary"
                          style={{ fontSize: "0.75rem", padding: "0.25rem 0.5rem" }}
                        >
                          Re-index
                        </button>
                        <button
                          onClick={() => {
                            if (confirm(`Delete document "${doc.title}"?`)) {
                              deleteMutation.mutate(doc.id);
                            }
                          }}
                          className="btn-ghost"
                          style={{ fontSize: "0.75rem", padding: "0.25rem 0.5rem", color: "var(--color-danger)" }}
                        >
                          ✕
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Error Details Modal */}
      {selectedError && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "hsla(222, 47%, 5%, 0.85)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
            padding: "1.5rem",
          }}
          onClick={() => setSelectedError(null)}
        >
          <div
            className="card-elevated"
            style={{ maxWidth: "580px", width: "100%", borderRadius: "var(--radius-xl)", padding: "1.75rem" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <h3 style={{ fontSize: "1.1rem", fontWeight: 700, margin: 0, color: "var(--color-danger)" }}>
                Extraction / Processing Error Diagnostic
              </h3>
              <button onClick={() => setSelectedError(null)} className="btn-ghost">✕</button>
            </div>
            <pre style={{ background: "var(--color-bg-overlay)", padding: "1rem", borderRadius: "var(--radius-md)", fontSize: "0.8rem", overflowX: "auto", color: "var(--color-text-secondary)", whiteSpace: "pre-wrap" }}>
              {selectedError}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
