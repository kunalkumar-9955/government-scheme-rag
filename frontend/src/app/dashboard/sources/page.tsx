"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { schemesApi } from "@/lib/api/endpoints";

export default function SourcesDirectoryPage() {
  const [searchTerm, setSearchTerm] = useState("");

  const { data: schemesRes, isLoading } = useQuery({
    queryKey: ["allSourcesDirectory"],
    queryFn: () => schemesApi.listSchemes({ page_size: 100 }),
    staleTime: 5 * 60 * 1000,
  });

  const schemes = schemesRes?.data?.results || [];

  const allSources: any[] = [];
  schemes.forEach((s: any) => {
    if (s.sources && Array.isArray(s.sources)) {
      s.sources.forEach((src: any) => {
        allSources.push({
          ...src,
          schemeName: s.name,
          schemeId: s.id,
          ministry: s.ministry?.name || "Central / State Ministry",
          category: s.category?.name || "General",
        });
      });
    }
    if (s.official_source_url) {
      allSources.push({
        title: `${s.short_title || s.name} Official Guidelines Portal`,
        url: s.official_source_url,
        source_type: "PORTAL_WEBPAGE",
        is_verified: true,
        schemeName: s.name,
        schemeId: s.id,
        ministry: s.ministry?.name || "Central / State Ministry",
        category: s.category?.name || "General",
      });
    }
  });

  const filteredSources = allSources.filter((src) => {
    if (!searchTerm.trim()) return true;
    const q = searchTerm.toLowerCase();
    return (
      src.title?.toLowerCase().includes(q) ||
      src.schemeName?.toLowerCase().includes(q) ||
      src.ministry?.toLowerCase().includes(q)
    );
  });

  return (
    <div style={{ padding: "2rem", height: "100%", overflowY: "auto" }}>
      {/* Header */}
      <div style={{ marginBottom: "2rem", display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "0 0 0.4rem" }}>
            📚 Official Government Sources & Evidence Repository
          </h1>
          <p style={{ color: "var(--color-text-secondary)", fontSize: "0.9rem" }}>
            Browse verified operational guidelines, gazette notifications, and official portals indexed in our RAG knowledge base.
          </p>
        </div>
      </div>

      {/* Search Input */}
      <div style={{ marginBottom: "1.5rem" }}>
        <input
          type="text"
          placeholder="🔍 Search verified documents by scheme, ministry, keyword..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="input-field"
          style={{ maxWidth: "480px" }}
        />
      </div>

      {/* Sources Grid */}
      {filteredSources.length === 0 ? (
        <div className="card" style={{ padding: "3rem 2rem", textAlign: "center", borderRadius: "var(--radius-xl)", border: "1px dashed var(--color-border)" }}>
          <span style={{ fontSize: "2.5rem", display: "block", marginBottom: "0.5rem" }}>📚</span>
          <h3 style={{ fontSize: "1.1rem", margin: "0 0 0.4rem" }}>No Source Documents Found</h3>
          <p style={{ color: "var(--color-text-secondary)", fontSize: "0.88rem" }}>
            Try searching for a different scheme name or clear your search term.
          </p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "1.25rem" }}>
          {filteredSources.map((src: any, idx: number) => (
            <div
              key={idx}
              className="card-elevated"
              style={{
                padding: "1.5rem",
                borderRadius: "var(--radius-xl)",
                border: "1px solid var(--color-border)",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
              }}
            >
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
                  <span className="badge badge-primary">{src.category}</span>
                  {src.is_verified && <span className="badge badge-success">✓ Verified Official Source</span>}
                </div>

                <h3 style={{ fontSize: "1.05rem", fontWeight: 700, margin: "0 0 0.35rem", color: "var(--color-text-primary)" }}>
                  {src.title || "Government Scheme Guideline"}
                </h3>
                <p style={{ fontSize: "0.85rem", color: "var(--color-primary)", fontWeight: 600, margin: "0 0 0.25rem" }}>
                  Scheme: {src.schemeName}
                </p>
                <p style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", margin: 0 }}>
                  Nodal Ministry: {src.ministry}
                </p>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid var(--color-border)", paddingTop: "0.75rem", marginTop: "1rem" }}>
                <Link
                  href={`/dashboard/chat?query=Explain the document '${encodeURIComponent(src.title)}' for ${encodeURIComponent(src.schemeName)}`}
                  className="btn-ghost"
                  style={{ fontSize: "0.78rem", textDecoration: "none" }}
                >
                  💬 Explain with AI
                </Link>
                {src.url ? (
                  <a
                    href={src.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-primary"
                    style={{ fontSize: "0.78rem", padding: "0.4rem 0.8rem", textDecoration: "none" }}
                  >
                    View Source ↗
                  </a>
                ) : (
                  <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)" }}>Gazette Document</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
