"use client";

import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { schemesApi } from "@/lib/api/endpoints";

export default function SavedSchemesPage() {
  const [savedIds, setSavedIds] = useState<string[]>([]);

  useEffect(() => {
    try {
      const stored = localStorage.getItem("saved_gov_schemes");
      if (stored) {
        setSavedIds(JSON.parse(stored));
      }
    } catch {}
  }, []);

  const { data: schemesRes, isLoading } = useQuery({
    queryKey: ["allSchemesForSaved"],
    queryFn: () => schemesApi.listSchemes({ page_size: 100 }),
    staleTime: 5 * 60 * 1000,
  });

  const allSchemes = schemesRes?.data?.results || [];
  const savedSchemes = allSchemes.filter((s: any) => savedIds.includes(s.id));

  const removeSavedScheme = (id: string) => {
    const updated = savedIds.filter((item) => item !== id);
    setSavedIds(updated);
    localStorage.setItem("saved_gov_schemes", JSON.stringify(updated));
  };

  return (
    <div style={{ padding: "2rem", height: "100%", overflowY: "auto" }}>
      {/* Header */}
      <div style={{ marginBottom: "2rem", display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "0 0 0.4rem" }}>
            ⭐ Saved Government Schemes
          </h1>
          <p style={{ color: "var(--color-text-secondary)", fontSize: "0.9rem" }}>
            Quickly access your bookmarked schemes, check real-time deadlines, and evaluate eligibility.
          </p>
        </div>
        <Link href="/dashboard/schemes" className="btn-secondary" style={{ fontSize: "0.85rem", textDecoration: "none" }}>
          🏛️ Browse All Schemes
        </Link>
      </div>

      {savedSchemes.length === 0 ? (
        <div className="card" style={{ padding: "3.5rem 2rem", textAlign: "center", borderRadius: "var(--radius-xl)", border: "1px dashed var(--color-border)" }}>
          <span style={{ fontSize: "3rem", display: "block", marginBottom: "0.75rem" }}>⭐</span>
          <h3 style={{ fontSize: "1.15rem", margin: "0 0 0.5rem" }}>No Saved Schemes Yet</h3>
          <p style={{ color: "var(--color-text-secondary)", fontSize: "0.88rem", maxWidth: "440px", margin: "0 auto 1.5rem", lineHeight: 1.6 }}>
            Browse through the official scheme directory and click the bookmark icon on any scheme to save it for quick review and eligibility tracking.
          </p>
          <Link href="/dashboard/schemes" className="btn-primary" style={{ padding: "0.6rem 1.25rem", textDecoration: "none" }}>
            Explore Verified Schemes →
          </Link>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "1.25rem" }}>
          {savedSchemes.map((scheme: any) => (
            <div
              key={scheme.id}
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
                  <span className="badge badge-primary">{scheme.category?.name || "General"}</span>
                  <button
                    onClick={() => removeSavedScheme(scheme.id)}
                    className="btn-ghost"
                    title="Remove from saved"
                    style={{ fontSize: "0.9rem", color: "var(--color-text-muted)" }}
                  >
                    ✕
                  </button>
                </div>

                <h3 style={{ fontSize: "1.1rem", fontWeight: 700, margin: "0 0 0.35rem", color: "var(--color-text-primary)" }}>
                  {scheme.name}
                </h3>
                <p style={{ fontSize: "0.82rem", color: "var(--color-text-secondary)", lineHeight: 1.5, marginBottom: "1rem" }}>
                  {scheme.description ? `${scheme.description.slice(0, 140)}...` : "Official welfare scheme."}
                </p>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid var(--color-border)", paddingTop: "0.75rem" }}>
                <Link
                  href={`/dashboard/chat?query=Tell me about ${encodeURIComponent(scheme.name)}`}
                  className="btn-ghost"
                  style={{ fontSize: "0.78rem", textDecoration: "none" }}
                >
                  💬 Ask AI
                </Link>
                <Link
                  href={`/dashboard/schemes/${scheme.id}`}
                  className="btn-primary"
                  style={{ fontSize: "0.78rem", padding: "0.4rem 0.8rem", textDecoration: "none" }}
                >
                  View Details →
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
