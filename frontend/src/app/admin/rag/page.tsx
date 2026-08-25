"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { documentsApi } from "@/lib/api/endpoints";

export default function AdminRAGPage() {
  const [searchChunk, setSearchChunk] = useState("");
  const [selectedDocFilter, setSelectedDocFilter] = useState("");
  const [expandedChunk, setExpandedChunk] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  // Fetch all documents for the document filter dropdown
  const { data: docsRes } = useQuery({
    queryKey: ["ragDocsList"],
    queryFn: () => documentsApi.listDocuments({ status: "COMPLETED" }),
  });
  const documents = docsRes?.data?.results || [];

  // Fetch global chunk pool
  const { data: chunksRes, isLoading, refetch } = useQuery({
    queryKey: ["adminGlobalChunks", { search: searchChunk, document: selectedDocFilter, page }],
    queryFn: () =>
      documentsApi.listGlobalChunks({
        search: searchChunk || undefined,
        document: selectedDocFilter || undefined,
        page,
      }),
    refetchInterval: 0,
  });

  const chunks: any[] = (chunksRes?.data?.data as any)?.results || (chunksRes?.data?.data as any[]) || [];
  const totalChunks = (chunksRes?.data?.data as any)?.count || chunks.length;

  return (
    <div style={{ padding: "2rem", height: "100%", overflowY: "auto" }}>
      {/* Header */}
      <div style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "0 0 0.4rem" }}>
          🧠 RAG Knowledge Base Inspector
        </h1>
        <p style={{ color: "var(--color-text-secondary)", fontSize: "0.9rem" }}>
          Inspect embedded document chunks in the vector store, search by keyword, filter by document, and verify retrieval grounding quality.
        </p>
      </div>

      {/* Summary Bar */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "1rem", marginBottom: "2rem" }}>
        <div className="card-elevated" style={{ padding: "1.25rem", borderRadius: "var(--radius-lg)", border: "1px solid var(--color-border)" }}>
          <span style={{ fontSize: "0.72rem", color: "var(--color-text-muted)", textTransform: "uppercase", fontWeight: 600 }}>Indexed Documents</span>
          <h3 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "0.2rem 0", color: "var(--color-success)" }}>
            {documents.length}
          </h3>
          <span style={{ fontSize: "0.72rem", color: "var(--color-text-muted)" }}>COMPLETED status</span>
        </div>
        <div className="card-elevated" style={{ padding: "1.25rem", borderRadius: "var(--radius-lg)", border: "1px solid var(--color-border)" }}>
          <span style={{ fontSize: "0.72rem", color: "var(--color-text-muted)", textTransform: "uppercase", fontWeight: 600 }}>Total Chunks Retrieved</span>
          <h3 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "0.2rem 0", color: "var(--color-primary)" }}>
            {totalChunks.toLocaleString()}
          </h3>
          <span style={{ fontSize: "0.72rem", color: "var(--color-text-muted)" }}>Across all indexed docs</span>
        </div>
        <div className="card-elevated" style={{ padding: "1.25rem", borderRadius: "var(--radius-lg)", border: "1px solid var(--color-border)" }}>
          <span style={{ fontSize: "0.72rem", color: "var(--color-text-muted)", textTransform: "uppercase", fontWeight: 600 }}>Chunk Embedding Model</span>
          <h3 style={{ fontSize: "1rem", fontWeight: 700, margin: "0.4rem 0", color: "var(--color-text-primary)" }}>
            text-embedding-004
          </h3>
          <span style={{ fontSize: "0.72rem", color: "var(--color-text-muted)" }}>Google Gemini Embedding</span>
        </div>
      </div>

      {/* Search & Filter Controls */}
      <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem", flexWrap: "wrap", alignItems: "center" }}>
        <input
          type="text"
          placeholder="🔍 Keyword search inside chunk content..."
          value={searchChunk}
          onChange={(e) => { setSearchChunk(e.target.value); setPage(1); }}
          className="input-field"
          style={{ maxWidth: "380px" }}
        />
        <select
          value={selectedDocFilter}
          onChange={(e) => { setSelectedDocFilter(e.target.value); setPage(1); }}
          className="input-field"
          style={{ maxWidth: "280px" }}
        >
          <option value="">All Documents ({documents.length})</option>
          {documents.map((d: any) => (
            <option key={d.id} value={d.id}>{d.title}</option>
          ))}
        </select>
        <button onClick={() => refetch()} className="btn-secondary" style={{ fontSize: "0.85rem" }}>
          ↻ Refresh
        </button>
      </div>

      {/* Chunks Table */}
      <div className="card-elevated" style={{ borderRadius: "var(--radius-xl)", overflow: "hidden", border: "1px solid var(--color-border)", marginBottom: "1.5rem" }}>
        {isLoading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: "3rem" }}>
            <div className="spinner" />
          </div>
        ) : chunks.length === 0 ? (
          <div style={{ padding: "3rem", textAlign: "center" }}>
            <span style={{ fontSize: "2rem", display: "block", marginBottom: "0.5rem" }}>🧠</span>
            <p style={{ color: "var(--color-text-muted)", fontSize: "0.88rem" }}>
              No chunks found. Upload and index a document first.
            </p>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--color-border)", textAlign: "left", background: "var(--color-bg-overlay)", color: "var(--color-text-muted)" }}>
                  <th style={{ padding: "0.85rem 1rem" }}>#</th>
                  <th style={{ padding: "0.85rem 1rem" }}>Document</th>
                  <th style={{ padding: "0.85rem 1rem" }}>Section</th>
                  <th style={{ padding: "0.85rem 1rem" }}>Type</th>
                  <th style={{ padding: "0.85rem 1rem" }}>Page</th>
                  <th style={{ padding: "0.85rem 1rem" }}>Tokens</th>
                  <th style={{ padding: "0.85rem 1rem" }}>Content Preview</th>
                </tr>
              </thead>
              <tbody>
                {chunks.map((chunk: any) => (
                  <>
                    <tr
                      key={chunk.id}
                      onClick={() => setExpandedChunk(expandedChunk === chunk.id ? null : chunk.id)}
                      style={{
                        borderBottom: "1px solid var(--color-border-subtle)",
                        cursor: "pointer",
                        background: expandedChunk === chunk.id ? "var(--color-bg-overlay)" : "transparent",
                      }}
                    >
                      <td style={{ padding: "0.75rem 1rem", color: "var(--color-text-muted)", fontFamily: "monospace" }}>
                        {chunk.chunk_index}
                      </td>
                      <td style={{ padding: "0.75rem 1rem", fontWeight: 600, maxWidth: "200px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {chunk.document?.title || chunk.document_title || "Document"}
                      </td>
                      <td style={{ padding: "0.75rem 1rem", color: "var(--color-text-secondary)", maxWidth: "180px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {chunk.section_title || "—"}
                      </td>
                      <td style={{ padding: "0.75rem 1rem" }}>
                        <span className="badge badge-primary" style={{ fontSize: "0.68rem" }}>
                          {chunk.chunk_type || "text"}
                        </span>
                      </td>
                      <td style={{ padding: "0.75rem 1rem", color: "var(--color-text-muted)" }}>
                        {chunk.page_number || "—"}
                      </td>
                      <td style={{ padding: "0.75rem 1rem", fontFamily: "monospace", fontWeight: 600 }}>
                        {chunk.token_count || "—"}
                      </td>
                      <td style={{ padding: "0.75rem 1rem", color: "var(--color-text-secondary)", maxWidth: "320px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {chunk.content?.slice(0, 120)}...
                      </td>
                    </tr>
                    {expandedChunk === chunk.id && (
                      <tr key={`${chunk.id}-expanded`}>
                        <td colSpan={7} style={{ padding: "0.5rem 1rem 1.25rem" }}>
                          <div style={{ background: "var(--color-bg-overlay)", padding: "1rem", borderRadius: "var(--radius-md)", borderLeft: "4px solid var(--color-primary)" }}>
                            <div style={{ fontSize: "0.72rem", color: "var(--color-text-muted)", marginBottom: "0.5rem", fontWeight: 600, textTransform: "uppercase" }}>
                              Full Chunk Content
                              {chunk.keywords?.length > 0 && ` · Keywords: ${chunk.keywords.join(", ")}`}
                            </div>
                            <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.8rem", color: "var(--color-text-secondary)", lineHeight: 1.6, margin: 0 }}>
                              {chunk.content}
                            </pre>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      <div style={{ display: "flex", justifyContent: "center", gap: "0.5rem" }}>
        <button
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page === 1}
          className="btn-secondary"
          style={{ padding: "0.4rem 0.9rem", fontSize: "0.82rem" }}
        >
          ← Prev
        </button>
        <span style={{ padding: "0.4rem 0.9rem", fontSize: "0.82rem", color: "var(--color-text-muted)" }}>
          Page {page}
        </span>
        <button
          onClick={() => setPage((p) => p + 1)}
          disabled={chunks.length < 20}
          className="btn-secondary"
          style={{ padding: "0.4rem 0.9rem", fontSize: "0.82rem" }}
        >
          Next →
        </button>
      </div>
    </div>
  );
}
