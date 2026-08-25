"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { schemesApi } from "@/lib/api/endpoints";
import type { Scheme } from "@/types";

export default function CompareSchemesPage() {
  const [selectedSchemeIds, setSelectedSchemeIds] = useState<string[]>([]);

  // Fetch list of schemes for selection dropdowns
  const { data: schemesRes } = useQuery({
    queryKey: ["allSchemesForCompare"],
    queryFn: () => schemesApi.listSchemes({ page_size: 100 }),
    staleTime: 5 * 60 * 1000,
  });

  const allSchemes = schemesRes?.data?.results || [];

  // Fetch detailed data for each selected scheme
  const { data: scheme1Res } = useQuery({
    queryKey: ["compareScheme", selectedSchemeIds[0]],
    queryFn: () => (selectedSchemeIds[0] ? schemesApi.getScheme(selectedSchemeIds[0]) : null),
    enabled: Boolean(selectedSchemeIds[0]),
  });

  const { data: scheme2Res } = useQuery({
    queryKey: ["compareScheme", selectedSchemeIds[1]],
    queryFn: () => (selectedSchemeIds[1] ? schemesApi.getScheme(selectedSchemeIds[1]) : null),
    enabled: Boolean(selectedSchemeIds[1]),
  });

  const { data: scheme3Res } = useQuery({
    queryKey: ["compareScheme", selectedSchemeIds[2]],
    queryFn: () => (selectedSchemeIds[2] ? schemesApi.getScheme(selectedSchemeIds[2]) : null),
    enabled: Boolean(selectedSchemeIds[2]),
  });

  const comparedSchemes: any[] = [
    scheme1Res?.data?.data,
    scheme2Res?.data?.data,
    scheme3Res?.data?.data,
  ].filter(Boolean);

  const handleSelectScheme = (index: number, id: string) => {
    const updated = [...selectedSchemeIds];
    if (id) {
      updated[index] = id;
    } else {
      updated.splice(index, 1);
    }
    setSelectedSchemeIds(updated);
  };

  return (
    <div style={{ padding: "2rem", height: "100%", overflowY: "auto" }}>
      {/* Header */}
      <div style={{ marginBottom: "2rem", display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "0 0 0.4rem" }}>
            ⚖️ Compare Government Schemes
          </h1>
          <p style={{ color: "var(--color-text-secondary)", fontSize: "0.9rem" }}>
            Select 2 or 3 government schemes to compare benefits, eligibility rules, required documents, and application procedures side-by-side.
          </p>
        </div>

        {comparedSchemes.length >= 2 && (
          <Link
            href={`/dashboard/chat?query=Compare ${encodeURIComponent(comparedSchemes.map((s) => s.name).join(" and "))}`}
            className="btn-primary"
            style={{ fontSize: "0.85rem", textDecoration: "none" }}
          >
            💬 Ask AI to Compare In Detail
          </Link>
        )}
      </div>

      {/* Selectors Bar */}
      <div
        className="card-elevated"
        style={{
          padding: "1.25rem",
          borderRadius: "var(--radius-xl)",
          marginBottom: "2rem",
          border: "1px solid var(--color-border)",
        }}
      >
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "1rem" }}>
          <div>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: "0.35rem" }}>
              Scheme 1 *
            </label>
            <select
              value={selectedSchemeIds[0] || ""}
              onChange={(e) => handleSelectScheme(0, e.target.value)}
              className="input-field"
            >
              <option value="">Select First Scheme</option>
              {allSchemes.map((s: any) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.category?.name || "General"})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: "0.35rem" }}>
              Scheme 2 *
            </label>
            <select
              value={selectedSchemeIds[1] || ""}
              onChange={(e) => handleSelectScheme(1, e.target.value)}
              className="input-field"
            >
              <option value="">Select Second Scheme</option>
              {allSchemes
                .filter((s: any) => s.id !== selectedSchemeIds[0])
                .map((s: any) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.category?.name || "General"})
                  </option>
                ))}
            </select>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: "0.35rem" }}>
              Scheme 3 (Optional)
            </label>
            <select
              value={selectedSchemeIds[2] || ""}
              onChange={(e) => handleSelectScheme(2, e.target.value)}
              className="input-field"
            >
              <option value="">Select Third Scheme</option>
              {allSchemes
                .filter((s: any) => s.id !== selectedSchemeIds[0] && s.id !== selectedSchemeIds[1])
                .map((s: any) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.category?.name || "General"})
                  </option>
                ))}
            </select>
          </div>
        </div>
      </div>

      {/* Comparison Grid */}
      {comparedSchemes.length === 0 ? (
        <div className="card" style={{ padding: "3rem", textAlign: "center", borderRadius: "var(--radius-xl)", border: "1px dashed var(--color-border)" }}>
          <span style={{ fontSize: "2.5rem", display: "block", marginBottom: "0.75rem" }}>⚖️</span>
          <h3 style={{ fontSize: "1.1rem", margin: "0 0 0.4rem" }}>No Schemes Selected</h3>
          <p style={{ color: "var(--color-text-secondary)", fontSize: "0.88rem", maxWidth: "420px", margin: "0 auto" }}>
            Choose at least two government schemes from the dropdown menus above to generate a side-by-side comparison matrix.
          </p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: `repeat(${comparedSchemes.length}, 1fr)`, gap: "1.25rem", alignItems: "start" }}>
          {comparedSchemes.map((scheme: any) => (
            <div
              key={scheme.id}
              className="card-elevated"
              style={{
                padding: "1.5rem",
                borderRadius: "var(--radius-xl)",
                border: "1px solid var(--color-border)",
                display: "flex",
                flexDirection: "column",
                gap: "1.25rem",
              }}
            >
              {/* Header */}
              <div>
                <span className="badge badge-primary" style={{ marginBottom: "0.4rem" }}>
                  {scheme.category?.name || "General"}
                </span>
                <h3 style={{ fontSize: "1.15rem", fontWeight: 700, margin: "0 0 0.35rem", color: "var(--color-text-primary)" }}>
                  {scheme.name}
                </h3>
                <p style={{ fontSize: "0.82rem", color: "var(--color-text-secondary)" }}>
                  {scheme.ministry?.name || "Central / State Ministry"}
                </p>
              </div>

              {/* Classification */}
              <div>
                <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--color-text-muted)", textTransform: "uppercase", marginBottom: "0.3rem" }}>
                  Scheme Classification
                </p>
                <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                  <span className="badge badge-accent">{scheme.scheme_type?.replace("_", " ") || "Central Sector"}</span>
                  {scheme.state && <span className="badge">{scheme.state.name}</span>}
                </div>
              </div>

              {/* Benefits */}
              <div>
                <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--color-success)", textTransform: "uppercase", marginBottom: "0.4rem" }}>
                  Financial & Support Benefits
                </p>
                {scheme.benefits?.length > 0 ? (
                  <ul style={{ margin: 0, paddingLeft: "1.2rem", fontSize: "0.82rem", color: "var(--color-text-secondary)", lineHeight: 1.6 }}>
                    {scheme.benefits.map((b: any, idx: number) => (
                      <li key={idx}>
                        <strong>{b.benefit_type || "Benefit"}:</strong> {b.description || b.amount_inr ? `₹${b.amount_inr}` : ""}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p style={{ fontSize: "0.82rem", color: "var(--color-text-secondary)", margin: 0 }}>
                    {scheme.description ? `${scheme.description.slice(0, 160)}...` : "Official welfare assistance."}
                  </p>
                )}
              </div>

              {/* Eligibility Rules */}
              <div>
                <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--color-primary)", textTransform: "uppercase", marginBottom: "0.4rem" }}>
                  Eligibility Criteria
                </p>
                {scheme.eligibility_rules?.length > 0 ? (
                  <ul style={{ margin: 0, paddingLeft: "1.2rem", fontSize: "0.82rem", color: "var(--color-text-secondary)", lineHeight: 1.6 }}>
                    {scheme.eligibility_rules.map((r: any, idx: number) => (
                      <li key={idx}>
                        {r.rule_description || `${r.criterion_key} ${r.operator} ${r.value}`}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p style={{ fontSize: "0.82rem", color: "var(--color-text-muted)", margin: 0 }}>
                    Standard resident qualifications apply.
                  </p>
                )}
              </div>

              {/* Required Documents */}
              <div>
                <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--color-text-muted)", textTransform: "uppercase", marginBottom: "0.4rem" }}>
                  Required Documents
                </p>
                {scheme.required_documents?.length > 0 ? (
                  <div style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap" }}>
                    {scheme.required_documents.map((d: any, idx: number) => (
                      <span key={idx} className="badge" style={{ fontSize: "0.75rem" }}>
                        📄 {d.document_name || d.name || "Aadhaar / ID"}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p style={{ fontSize: "0.82rem", color: "var(--color-text-muted)", margin: 0 }}>
                    Aadhaar, Bank Account, Proof of Residence.
                  </p>
                )}
              </div>

              {/* Official Portals & Actions */}
              <div style={{ borderTop: "1px solid var(--color-border)", paddingTop: "1rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                {scheme.official_application_url || scheme.official_source_url ? (
                  <a
                    href={scheme.official_application_url || scheme.official_source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-primary"
                    style={{ fontSize: "0.78rem", padding: "0.4rem 0.8rem", textDecoration: "none" }}
                  >
                    Official Portal ↗
                  </a>
                ) : (
                  <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)" }}>Central Portal</span>
                )}
                <Link
                  href={`/dashboard/schemes/${scheme.id}`}
                  className="btn-secondary"
                  style={{ fontSize: "0.78rem", padding: "0.4rem 0.8rem", textDecoration: "none" }}
                >
                  Full View →
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
