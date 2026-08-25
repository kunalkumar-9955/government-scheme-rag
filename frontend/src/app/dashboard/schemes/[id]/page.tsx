"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { schemesApi, eligibilityApi } from "@/lib/api/endpoints";

export default function SchemeDetailPage() {
  const params = useParams();
  const router = useRouter();
  const schemeId = params.id as string;

  const [eligibilityResult, setEligibilityResult] = useState<any | null>(null);
  const [isSaved, setIsSaved] = useState(false);

  // Check saved state
  useState(() => {
    try {
      const stored = localStorage.getItem("saved_gov_schemes");
      if (stored && JSON.parse(stored).includes(schemeId)) {
        setIsSaved(true);
      }
    } catch {}
  });

  const toggleSave = () => {
    try {
      const stored = localStorage.getItem("saved_gov_schemes");
      let list: string[] = stored ? JSON.parse(stored) : [];
      if (list.includes(schemeId)) {
        list = list.filter((id) => id !== schemeId);
        setIsSaved(false);
      } else {
        list.push(schemeId);
        setIsSaved(true);
      }
      localStorage.setItem("saved_gov_schemes", JSON.stringify(list));
    } catch {}
  };

  const { data, isLoading, error } = useQuery({
    queryKey: ["schemeDetail", schemeId],
    queryFn: () => schemesApi.getScheme(schemeId),
    enabled: Boolean(schemeId),
  });

  const checkEligibilityMutation = useMutation({
    mutationFn: () => eligibilityApi.checkForScheme(schemeId),
    onSuccess: (res) => {
      setEligibilityResult(res.data?.data);
    },
  });

  const scheme: any = data?.data?.data;

  if (isLoading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100%" }}>
        <div className="spinner" style={{ width: 36, height: 36 }} />
      </div>
    );
  }

  if (error || !scheme) {
    return (
      <div style={{ padding: "3rem", textAlign: "center" }}>
        <h2 style={{ fontSize: "1.3rem", color: "var(--color-danger)", marginBottom: "0.5rem" }}>Scheme Not Found</h2>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "1.5rem" }}>
          The requested government scheme record could not be loaded.
        </p>
        <button onClick={() => router.push("/dashboard/schemes")} className="btn-primary">
          ← Back to Schemes
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: "2rem", height: "100%", overflowY: "auto" }}>
      {/* Top Breadcrumb & Actions */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <button onClick={() => router.back()} className="btn-ghost" style={{ fontSize: "0.85rem", padding: "0.4rem 0.75rem" }}>
          ← Back
        </button>

        <div style={{ display: "flex", gap: "0.6rem" }}>
          <button
            onClick={toggleSave}
            className={`btn-secondary ${isSaved ? "border-primary" : ""}`}
            style={{ fontSize: "0.85rem" }}
          >
            {isSaved ? "⭐ Saved" : "☆ Save Scheme"}
          </button>
          <Link
            href={`/dashboard/chat?query=Tell me about ${encodeURIComponent(scheme.name)}`}
            className="btn-primary"
            style={{ fontSize: "0.85rem", textDecoration: "none" }}
          >
            💬 Ask AI Assistant
          </Link>
        </div>
      </div>

      {/* Main Scheme Hero */}
      <div
        className="card-elevated"
        style={{
          padding: "2rem",
          borderRadius: "var(--radius-xl)",
          marginBottom: "2rem",
          border: "1px solid var(--color-border)",
        }}
      >
        <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem", flexWrap: "wrap" }}>
          <span className="badge badge-primary">{scheme.category?.name || "General Category"}</span>
          <span className="badge badge-accent">{scheme.scheme_type?.replace("_", " ") || "Central Sector"}</span>
          {scheme.state && <span className="badge">{scheme.state.name}</span>}
          <span className="badge badge-success">{scheme.status}</span>
        </div>

        <h1 style={{ fontSize: "1.85rem", fontWeight: 700, margin: "0 0 0.5rem", color: "var(--color-text-primary)" }}>
          {scheme.name}
        </h1>
        {scheme.short_title && (
          <p style={{ fontSize: "1rem", color: "var(--color-primary)", fontWeight: 600, margin: "0 0 0.5rem" }}>
            Abbreviation: {scheme.short_title}
          </p>
        )}
        <p style={{ fontSize: "0.92rem", color: "var(--color-text-secondary)", lineHeight: 1.7, maxWidth: "800px" }}>
          {scheme.description}
        </p>

        {/* Nodal Ministry / Dept info */}
        <div style={{ display: "flex", gap: "2rem", borderTop: "1px solid var(--color-border)", paddingTop: "1rem", marginTop: "1.5rem", flexWrap: "wrap" }}>
          <div>
            <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", textTransform: "uppercase" }}>Nodal Ministry</span>
            <p style={{ fontSize: "0.9rem", fontWeight: 600, margin: "0.2rem 0 0" }}>
              {scheme.ministry?.name || "Government of India"}
            </p>
          </div>
          {scheme.department && (
            <div>
              <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", textTransform: "uppercase" }}>Department</span>
              <p style={{ fontSize: "0.9rem", fontWeight: 600, margin: "0.2rem 0 0" }}>
                {scheme.department.name}
              </p>
            </div>
          )}
          {scheme.version && (
            <div>
              <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", textTransform: "uppercase" }}>Guideline Version</span>
              <p style={{ fontSize: "0.9rem", fontWeight: 600, margin: "0.2rem 0 0" }}>
                v{scheme.version}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* 1-Click Eligibility Check Banner */}
      <div
        className="card-elevated"
        style={{
          padding: "1.5rem",
          borderRadius: "var(--radius-xl)",
          marginBottom: "2rem",
          background: "var(--color-bg-overlay)",
          border: "1px solid var(--color-border)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1rem",
        }}
      >
        <div>
          <h3 style={{ fontSize: "1.1rem", fontWeight: 700, margin: "0 0 0.25rem" }}>
            Check Your Eligibility For This Scheme
          </h3>
          <p style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", margin: 0 }}>
            Instantly evaluate your saved citizen profile against this scheme's official rules.
          </p>
        </div>
        <button
          onClick={() => checkEligibilityMutation.mutate()}
          disabled={checkEligibilityMutation.isPending}
          className="btn-primary"
          style={{ padding: "0.6rem 1.25rem", fontWeight: 600 }}
        >
          {checkEligibilityMutation.isPending ? "Evaluating..." : "🔍 Check My Eligibility"}
        </button>
      </div>

      {/* Eligibility Result Alert */}
      {eligibilityResult && (
        <div
          className="card-elevated"
          style={{
            padding: "1.5rem",
            borderRadius: "var(--radius-xl)",
            marginBottom: "2rem",
            border: "1px solid var(--color-border)",
            borderLeft:
              eligibilityResult.verdict === "Likely Eligible" || eligibilityResult.verdict === "Eligible"
                ? "5px solid var(--color-success)"
                : eligibilityResult.verdict === "Possibly Eligible"
                ? "5px solid var(--color-accent)"
                : eligibilityResult.verdict === "Insufficient Information"
                ? "5px solid var(--color-primary)"
                : "5px solid var(--color-danger)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
            <span className="badge badge-primary">{eligibilityResult.verdict}</span>
            <span style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)" }}>
              {eligibilityResult.passed_rules?.length || 0} Passed • {eligibilityResult.failed_rules?.length || 0} Failed
            </span>
          </div>
          <p style={{ fontSize: "0.9rem", lineHeight: 1.6, margin: "0 0 1rem" }}>
            {eligibilityResult.summary_explanation}
          </p>
          <Link
            href="/dashboard/find-schemes"
            style={{ fontSize: "0.8rem", color: "var(--color-primary)", textDecoration: "underline" }}
          >
            Adjust Criteria in 'Find Schemes For Me' →
          </Link>
        </div>
      )}

      {/* Structured Sections Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", alignItems: "start" }}>
        {/* Left Column: Benefits & Eligibility */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {/* Benefits */}
          <div className="card-elevated" style={{ padding: "1.5rem", borderRadius: "var(--radius-xl)", border: "1px solid var(--color-border)" }}>
            <h3 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "1rem", color: "var(--color-success)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              💰 Scheme Benefits
            </h3>
            {scheme.benefits?.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                {scheme.benefits.map((b: any, idx: number) => (
                  <div key={idx} style={{ background: "var(--color-bg-overlay)", padding: "0.75rem 1rem", borderRadius: "var(--radius-md)", borderLeft: "3px solid var(--color-success)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.25rem" }}>
                      <strong style={{ fontSize: "0.85rem" }}>{b.benefit_type || "Direct Benefit"}</strong>
                      {b.amount_inr && <span style={{ fontWeight: 700, color: "var(--color-success)" }}>₹{b.amount_inr}</span>}
                    </div>
                    <p style={{ fontSize: "0.82rem", color: "var(--color-text-secondary)", margin: 0 }}>
                      {b.description}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", margin: 0 }}>
                Financial and welfare assistance provided per official operational guidelines.
              </p>
            )}
          </div>

          {/* Eligibility Rules */}
          <div className="card-elevated" style={{ padding: "1.5rem", borderRadius: "var(--radius-xl)", border: "1px solid var(--color-border)" }}>
            <h3 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "1rem", color: "var(--color-primary)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              📋 Eligibility Criteria Rules
            </h3>
            {scheme.eligibility_rules?.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                {scheme.eligibility_rules.map((r: any, idx: number) => (
                  <div key={idx} style={{ background: "var(--color-bg-overlay)", padding: "0.75rem 1rem", borderRadius: "var(--radius-md)", fontSize: "0.82rem", lineHeight: 1.5 }}>
                    <strong>{r.criterion_key}</strong>: {r.rule_description || `${r.operator} ${r.value}`}
                    {r.is_mandatory && <span className="badge badge-accent" style={{ marginLeft: "0.5rem", fontSize: "0.7rem" }}>Mandatory</span>}
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", margin: 0 }}>
                Open to eligible citizens meeting demographic and residence qualifications.
              </p>
            )}
          </div>
        </div>

        {/* Right Column: Required Documents, Application Procedure, Sources */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {/* Required Documents */}
          <div className="card-elevated" style={{ padding: "1.5rem", borderRadius: "var(--radius-xl)", border: "1px solid var(--color-border)" }}>
            <h3 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              📄 Required Documents
            </h3>
            {scheme.required_documents?.length > 0 ? (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.6rem" }}>
                {scheme.required_documents.map((d: any, idx: number) => (
                  <div key={idx} style={{ background: "var(--color-bg-overlay)", padding: "0.6rem 0.8rem", borderRadius: "var(--radius-md)", fontSize: "0.82rem" }}>
                    ✓ {d.document_name || d.name}
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", margin: 0 }}>
                Aadhaar card, Proof of Residence, Bank Passbook, and category certificate.
              </p>
            )}
          </div>

          {/* Application Procedure */}
          <div className="card-elevated" style={{ padding: "1.5rem", borderRadius: "var(--radius-xl)", border: "1px solid var(--color-border)" }}>
            <h3 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              🚀 How to Apply
            </h3>
            {scheme.application_procedure?.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                {scheme.application_procedure.map((step: any, idx: number) => (
                  <div key={idx} style={{ display: "flex", gap: "0.75rem", alignItems: "flex-start" }}>
                    <div style={{ width: 24, height: 24, borderRadius: "50%", background: "var(--color-primary)", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.75rem", fontWeight: 700, flexShrink: 0 }}>
                      {step.step_number || idx + 1}
                    </div>
                    <div>
                      <strong style={{ fontSize: "0.85rem", display: "block" }}>{step.title || `Step ${idx + 1}`}</strong>
                      <p style={{ fontSize: "0.82rem", color: "var(--color-text-secondary)", margin: "0.2rem 0 0", lineHeight: 1.5 }}>
                        {step.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", margin: 0, lineHeight: 1.6 }}>
                Apply online through the official government portal or visit your nearest Common Service Centre (CSC).
              </p>
            )}

            {/* Official Portal Buttons */}
            <div style={{ marginTop: "1.5rem", borderTop: "1px solid var(--color-border)", paddingTop: "1rem", display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
              {scheme.official_application_url && (
                <a
                  href={scheme.official_application_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-primary"
                  style={{ textDecoration: "none", fontSize: "0.85rem" }}
                >
                  Apply on Official Portal ↗
                </a>
              )}
              {scheme.official_source_url && (
                <a
                  href={scheme.official_source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-secondary"
                  style={{ textDecoration: "none", fontSize: "0.85rem" }}
                >
                  View Official Guidelines ↗
                </a>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
