"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { schemesApi } from "@/lib/api/endpoints";
import type { GovernmentScheme } from "@/types";

export default function SchemesPage() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [schemeType, setSchemeType] = useState("");
  const [page, setPage] = useState(1);
  const [selectedSchemeId, setSelectedSchemeId] = useState<string | null>(null);

  // Fetch categories dynamically
  const { data: catData } = useQuery({
    queryKey: ["schemeCategories"],
    queryFn: () => schemesApi.getCategories(),
  });
  const categories = catData?.data || [];

  // Fetch schemes list
  const { data, isLoading, error } = useQuery({
    queryKey: ["schemes", { search, category, schemeType, page }],
    queryFn: () =>
      schemesApi.listSchemes({
        search,
        category: category || undefined,
        scheme_type: schemeType || undefined,
        page,
        page_size: 12,
      }),
    staleTime: 2 * 60 * 1000,
  });

  // Fetch detailed scheme when modal is opened
  const { data: detailData, isLoading: isLoadingDetail } = useQuery({
    queryKey: ["schemeDetail", selectedSchemeId],
    queryFn: () => (selectedSchemeId ? schemesApi.getScheme(selectedSchemeId) : null),
    enabled: Boolean(selectedSchemeId),
  });

  const schemes: GovernmentScheme[] = data?.data?.results || [];
  const totalCount = data?.data?.count || 0;
  const totalPages = data?.data?.total_pages || 1;
  const activeDetail = detailData?.data?.data;

  return (
    <div style={{ padding: "2rem", height: "100%", overflowY: "auto" }}>
      {/* Header */}
      <div style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "1.75rem", marginBottom: "0.5rem" }}>Browse Government Schemes</h1>
        <p style={{ color: "var(--color-text-secondary)" }}>
          {totalCount > 0
            ? `${totalCount} verified schemes available with structured eligibility criteria`
            : "Discover schemes you may be eligible for"}
        </p>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        <input
          type="text"
          placeholder="🔍 Search schemes by name, keyword (e.g. kisan, housing)..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="input-field"
          style={{ maxWidth: 360 }}
        />
        <select
          value={category}
          onChange={(e) => {
            setCategory(e.target.value);
            setPage(1);
          }}
          className="input-field"
          style={{ maxWidth: 240 }}
        >
          <option value="">All Categories ({categories.length})</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.icon} {c.name} {c.schemes_count !== undefined ? `(${c.schemes_count})` : ""}
            </option>
          ))}
        </select>
        <select
          value={schemeType}
          onChange={(e) => {
            setSchemeType(e.target.value);
            setPage(1);
          }}
          className="input-field"
          style={{ maxWidth: 200 }}
        >
          <option value="">All Types</option>
          <option value="CENTRAL_SECTOR">Central Sector (100% Central)</option>
          <option value="CENTRALLY_SPONSORED">Centrally Sponsored</option>
          <option value="STATE_GOVERNMENT">State Scheme</option>
        </select>
      </div>

      {/* Scheme Grid */}
      {isLoading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "1.25rem" }}>
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="card" style={{ height: 220, opacity: 0.4, animation: "glowPulse 1.5s ease infinite" }} />
          ))}
        </div>
      ) : error ? (
        <div className="card" style={{ textAlign: "center", padding: "3rem", color: "var(--color-text-muted)" }}>
          <p style={{ fontSize: "2rem" }}>📭</p>
          <p>Could not load schemes. Backend may not be reachable.</p>
        </div>
      ) : schemes.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "3rem", color: "var(--color-text-muted)" }}>
          <p style={{ fontSize: "2rem" }}>🏛️</p>
          <p>No schemes matched your search criteria.</p>
        </div>
      ) : (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "1.25rem" }}>
            {schemes.map((scheme, i) => (
              <motion.div
                key={scheme.id}
                className="card"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                whileHover={{ y: -3, borderColor: "var(--color-primary)" }}
                onClick={() => setSelectedSchemeId(scheme.id)}
                style={{ cursor: "pointer", display: "flex", flexDirection: "column", justifyContent: "space-between" }}
              >
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
                    <span className="badge badge-primary" style={{ fontSize: "0.7rem" }}>
                      {scheme.category_icon} {scheme.category_name || "General"}
                    </span>
                    <span className="badge badge-success" style={{ fontSize: "0.7rem" }}>
                      {scheme.status_display || scheme.status}
                    </span>
                  </div>

                  <h3 style={{ fontSize: "1.05rem", marginBottom: "0.3rem", lineHeight: 1.35 }}>
                    {scheme.short_title ? `${scheme.short_title} — ` : ""}
                    {scheme.name}
                  </h3>

                  <p style={{ fontSize: "0.78rem", color: "var(--color-text-muted)", marginBottom: "0.75rem" }}>
                    🏛️ {scheme.ministry_name || "Ministry of India"}
                  </p>

                  <p
                    style={{
                      fontSize: "0.82rem",
                      color: "var(--color-text-secondary)",
                      lineHeight: 1.5,
                      display: "-webkit-box",
                      WebkitLineClamp: 3,
                      WebkitBoxOrient: "vertical",
                      overflow: "hidden",
                    }}
                  >
                    {scheme.description}
                  </p>
                </div>

                <div
                  style={{
                    marginTop: "1rem",
                    paddingTop: "0.75rem",
                    borderTop: "1px solid var(--color-border)",
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: "0.75rem",
                    color: "var(--color-text-muted)",
                  }}
                >
                  <span>📜 {scheme.eligibility_rules_count || 0} Rules</span>
                  <span>🎁 {scheme.benefits_count || 0} Benefits</span>
                  <span>📄 {scheme.required_documents_count || 0} Docs</span>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div style={{ display: "flex", justifyContent: "center", gap: "0.5rem", marginTop: "2.5rem" }}>
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn-secondary"
                style={{ padding: "0.5rem 1rem" }}
              >
                ← Prev
              </button>
              <span style={{ padding: "0.5rem 1rem", color: "var(--color-text-muted)", fontSize: "0.875rem" }}>
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="btn-secondary"
                style={{ padding: "0.5rem 1rem" }}
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}

      {/* Scheme Detail Modal */}
      <AnimatePresence>
        {selectedSchemeId && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{
              position: "fixed",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: "rgba(0, 0, 0, 0.7)",
              backdropFilter: "blur(4px)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 100,
              padding: "1.5rem",
            }}
            onClick={() => setSelectedSchemeId(null)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 15 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 15 }}
              onClick={(e) => e.stopPropagation()}
              className="card-elevated"
              style={{
                width: "100%",
                maxWidth: "800px",
                maxHeight: "85vh",
                overflowY: "auto",
                borderRadius: "var(--radius-xl)",
                padding: "2rem",
              }}
            >
              {isLoadingDetail || !activeDetail ? (
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", padding: "3rem", justifyContent: "center" }}>
                  <div className="spinner" />
                  <span>Loading scheme details...</span>
                </div>
              ) : (
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
                    <div>
                      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.5rem" }}>
                        <span className="badge badge-primary">{activeDetail.category_details?.name || "General"}</span>
                        <span className="badge badge-success">{activeDetail.status_display}</span>
                        <span className="badge">{activeDetail.scheme_type_display}</span>
                      </div>
                      <h2 style={{ fontSize: "1.4rem", margin: 0 }}>
                        {activeDetail.short_title ? `${activeDetail.short_title} — ` : ""}
                        {activeDetail.name}
                      </h2>
                      <p style={{ color: "var(--color-text-muted)", fontSize: "0.85rem", marginTop: "0.25rem" }}>
                        🏛️ {activeDetail.ministry_details?.name}
                      </p>
                    </div>
                    <button onClick={() => setSelectedSchemeId(null)} className="btn-secondary" style={{ padding: "0.3rem 0.6rem" }}>
                      ✕
                    </button>
                  </div>

                  <p style={{ fontSize: "0.9rem", lineHeight: 1.6, color: "var(--color-text-secondary)", marginBottom: "1.5rem" }}>
                    {activeDetail.description}
                  </p>

                  {/* Benefits */}
                  {activeDetail.benefits && activeDetail.benefits.length > 0 && (
                    <div style={{ marginBottom: "1.5rem" }}>
                      <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.75rem" }}>🎁 Key Benefits</h3>
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                        {activeDetail.benefits.map((b) => (
                          <div key={b.id} className="card" style={{ padding: "0.75rem 1rem", background: "var(--color-bg-overlay)" }}>
                            <div style={{ fontWeight: 600, fontSize: "0.88rem" }}>{b.title}</div>
                            <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginTop: "0.25rem" }}>
                              {b.description}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Eligibility Rules */}
                  {activeDetail.eligibility_rules && activeDetail.eligibility_rules.length > 0 && (
                    <div style={{ marginBottom: "1.5rem" }}>
                      <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.75rem" }}>📜 Eligibility Rules</h3>
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                        {activeDetail.eligibility_rules.map((r) => (
                          <div key={r.id} style={{ display: "flex", alignItems: "flex-start", gap: "0.5rem", fontSize: "0.85rem" }}>
                            <span style={{ color: "var(--color-primary-light)" }}>●</span>
                            <span>
                              <strong>{r.criterion_key}:</strong> {r.rule_description}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Required Documents */}
                  {activeDetail.required_documents && activeDetail.required_documents.length > 0 && (
                    <div style={{ marginBottom: "1.5rem" }}>
                      <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.75rem" }}>📄 Required Documents</h3>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                        {activeDetail.required_documents.map((d) => (
                          <span key={d.id} className="badge" style={{ fontSize: "0.8rem", padding: "0.35rem 0.75rem" }}>
                            📋 {d.document_name} {d.is_mandatory ? "(Mandatory)" : "(Optional)"}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  <div style={{ display: "flex", gap: "1rem", marginTop: "2rem", paddingTop: "1rem", borderTop: "1px solid var(--color-border)", flexWrap: "wrap", alignItems: "center" }}>
                    {activeDetail.official_application_url && (
                      <a href={activeDetail.official_application_url} target="_blank" rel="noopener noreferrer" style={{ textDecoration: "none" }}>
                        <button className="btn-primary" style={{ fontSize: "0.9rem" }}>
                          Apply on Official Portal ↗
                        </button>
                      </a>
                    )}
                    {activeDetail.official_source_url && (
                      <a href={activeDetail.official_source_url} target="_blank" rel="noopener noreferrer" style={{ textDecoration: "none" }}>
                        <button className="btn-secondary" style={{ fontSize: "0.9rem" }}>
                          Official Source Guidelines ↗
                        </button>
                      </a>
                    )}
                    <Link href={`/dashboard/schemes/${activeDetail.id}`} style={{ textDecoration: "none", marginLeft: "auto" }}>
                      <button className="btn-ghost" style={{ fontSize: "0.88rem" }}>
                        Open Full Dedicated Page →
                      </button>
                    </Link>
                  </div>
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
