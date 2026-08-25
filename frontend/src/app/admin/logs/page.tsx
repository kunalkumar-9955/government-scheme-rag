"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "@/lib/api/endpoints";

const QUERY_TYPES = ["general", "eligibility", "scheme_discovery", "benefits", "documents", "comparison", "application", "follow_up"];

export default function AdminQueryLogsPage() {
  const [search, setSearch] = useState("");
  const [queryTypeFilter, setQueryTypeFilter] = useState("");
  const [failedOnly, setFailedOnly] = useState(false);
  const [expandedLog, setExpandedLog] = useState<string | null>(null);

  const { data: logsRes, isLoading, refetch } = useQuery({
    queryKey: ["adminQueryLogs", { search, queryTypeFilter, failedOnly }],
    queryFn: () =>
      analyticsApi.getQueryLogs({
        search: search || undefined,
        query_type: queryTypeFilter || undefined,
        failed_only: failedOnly ? "1" : undefined,
      }),
    refetchInterval: 15000,
  });

  const logs: any[] = (logsRes?.data?.data as any[]) || [];
  const failedCount = logs.filter((l: any) => l.faithfulness != null && l.faithfulness < 0.5).length;
  const faithfulLogs = logs.filter((l: any) => l.faithfulness != null);
  const avgFaithfulness = faithfulLogs.length
    ? (faithfulLogs.reduce((a: number, l: any) => a + l.faithfulness, 0) / faithfulLogs.length) * 100
    : null;

  return (
    <div style={{ padding: "2rem", height: "100%", overflowY: "auto" }}>
      {/* Header */}
      <div style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "0 0 0.4rem" }}>
          📋 Query Logs, Retrieval Audits & Security Monitoring
        </h1>
        <p style={{ color: "var(--color-text-secondary)", fontSize: "0.9rem" }}>
          Comprehensive per-query inspection of citizen AI queries — classified intents, faithfulness scores, retrieval performance, and failure diagnostics.
        </p>
      </div>

      {/* Quick Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: "1rem", marginBottom: "2rem" }}>
        <div className="card-elevated" style={{ padding: "1.25rem", borderRadius: "var(--radius-lg)", border: "1px solid var(--color-border)" }}>
          <span style={{ fontSize: "0.72rem", color: "var(--color-text-muted)", textTransform: "uppercase", fontWeight: 600 }}>Total Queries (Visible)</span>
          <h3 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "0.2rem 0", color: "var(--color-primary)" }}>{logs.length}</h3>
        </div>
        <div className="card-elevated" style={{ padding: "1.25rem", borderRadius: "var(--radius-lg)", border: "1px solid var(--color-border)" }}>
          <span style={{ fontSize: "0.72rem", color: "var(--color-text-muted)", textTransform: "uppercase", fontWeight: 600 }}>Failed (Low Faithfulness)</span>
          <h3 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "0.2rem 0", color: "var(--color-danger)" }}>{failedCount}</h3>
        </div>
        <div className="card-elevated" style={{ padding: "1.25rem", borderRadius: "var(--radius-lg)", border: "1px solid var(--color-border)" }}>
          <span style={{ fontSize: "0.72rem", color: "var(--color-text-muted)", textTransform: "uppercase", fontWeight: 600 }}>Avg Faithfulness</span>
          <h3 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "0.2rem 0", color: "var(--color-success)" }}>
            {avgFaithfulness != null ? `${avgFaithfulness.toFixed(1)}%` : "N/A"}
          </h3>
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: "1rem", marginBottom: "1.25rem", flexWrap: "wrap", alignItems: "center" }}>
        <input
          type="text"
          placeholder="🔍 Search queries..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input-field"
          style={{ maxWidth: "320px" }}
        />
        <select
          value={queryTypeFilter}
          onChange={(e) => setQueryTypeFilter(e.target.value)}
          className="input-field"
          style={{ maxWidth: "220px" }}
        >
          <option value="">All Intent Types</option>
          {QUERY_TYPES.map((qt) => (
            <option key={qt} value={qt}>{qt}</option>
          ))}
        </select>
        <label style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.82rem", cursor: "pointer", fontWeight: 500 }}>
          <input
            type="checkbox"
            checked={failedOnly}
            onChange={(e) => setFailedOnly(e.target.checked)}
          />
          Show Failed Queries Only
        </label>
        <button onClick={() => refetch()} className="btn-secondary" style={{ fontSize: "0.82rem" }}>
          ↻ Refresh
        </button>
      </div>

      {/* Logs Table */}
      <div className="card-elevated" style={{ borderRadius: "var(--radius-xl)", overflow: "hidden", border: "1px solid var(--color-border)" }}>
        {isLoading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: "3rem" }}>
            <div className="spinner" />
          </div>
        ) : logs.length === 0 ? (
          <div style={{ padding: "3rem", textAlign: "center" }}>
            <span style={{ fontSize: "2rem", display: "block", marginBottom: "0.5rem" }}>📋</span>
            <p style={{ color: "var(--color-text-muted)", fontSize: "0.88rem" }}>No query logs found.</p>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--color-border)", textAlign: "left", background: "var(--color-bg-overlay)", color: "var(--color-text-muted)" }}>
                  <th style={{ padding: "0.85rem 1rem" }}>Query</th>
                  <th style={{ padding: "0.85rem 1rem" }}>Intent</th>
                  <th style={{ padding: "0.85rem 1rem" }}>Faithfulness</th>
                  <th style={{ padding: "0.85rem 1rem" }}>Answer Rel.</th>
                  <th style={{ padding: "0.85rem 1rem" }}>Ctx Precision</th>
                  <th style={{ padding: "0.85rem 1rem" }}>Confidence</th>
                  <th style={{ padding: "0.85rem 1rem" }}>Latency</th>
                  <th style={{ padding: "0.85rem 1rem" }}>Time</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log: any) => {
                  const isLowFaith = log.faithfulness != null && log.faithfulness < 0.5;
                  return (
                    <>
                      <tr
                        key={log.id}
                        onClick={() => setExpandedLog(expandedLog === log.id ? null : log.id)}
                        style={{
                          borderBottom: "1px solid var(--color-border-subtle)",
                          cursor: "pointer",
                          background: isLowFaith
                            ? "hsla(0, 72%, 51%, 0.04)"
                            : expandedLog === log.id
                            ? "var(--color-bg-overlay)"
                            : "transparent",
                        }}
                      >
                        <td style={{ padding: "0.75rem 1rem", maxWidth: "280px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontWeight: 500 }}>
                          {log.query}
                        </td>
                        <td style={{ padding: "0.75rem 1rem" }}>
                          <span className="badge badge-primary" style={{ fontSize: "0.68rem" }}>
                            {log.query_type || "general"}
                          </span>
                        </td>
                        <td style={{ padding: "0.75rem 1rem" }}>
                          {log.faithfulness != null ? (
                            <span style={{ fontWeight: 600, color: log.faithfulness >= 0.8 ? "var(--color-success)" : log.faithfulness >= 0.5 ? "var(--color-accent)" : "var(--color-danger)" }}>
                              {(log.faithfulness * 100).toFixed(1)}%
                            </span>
                          ) : (
                            <span style={{ color: "var(--color-text-muted)" }}>—</span>
                          )}
                        </td>
                        <td style={{ padding: "0.75rem 1rem" }}>
                          {log.answer_relevancy != null
                            ? <span style={{ color: "var(--color-text-secondary)" }}>{(log.answer_relevancy * 100).toFixed(1)}%</span>
                            : <span style={{ color: "var(--color-text-muted)" }}>—</span>}
                        </td>
                        <td style={{ padding: "0.75rem 1rem" }}>
                          {log.context_precision != null
                            ? <span style={{ color: "var(--color-text-secondary)" }}>{(log.context_precision * 100).toFixed(1)}%</span>
                            : <span style={{ color: "var(--color-text-muted)" }}>—</span>}
                        </td>
                        <td style={{ padding: "0.75rem 1rem" }}>
                          {log.confidence_score != null
                            ? `${(log.confidence_score * 100).toFixed(0)}%`
                            : <span style={{ color: "var(--color-text-muted)" }}>—</span>}
                        </td>
                        <td style={{ padding: "0.75rem 1rem", color: "var(--color-text-muted)" }}>
                          {log.latency_ms ? `${log.latency_ms}ms` : "—"}
                        </td>
                        <td style={{ padding: "0.75rem 1rem", color: "var(--color-text-muted)", whiteSpace: "nowrap" }}>
                          {log.created_at ? new Date(log.created_at).toLocaleString("en-IN", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "short" }) : "—"}
                        </td>
                      </tr>
                      {expandedLog === log.id && (
                        <tr key={`${log.id}-expanded`}>
                          <td colSpan={8} style={{ padding: "0.5rem 1rem 1.25rem" }}>
                            <div style={{ background: "var(--color-bg-overlay)", padding: "1rem", borderRadius: "var(--radius-md)", borderLeft: `4px solid ${isLowFaith ? "var(--color-danger)" : "var(--color-primary)"}` }}>
                              <p style={{ fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.4rem" }}>Full Query:</p>
                              <p style={{ fontSize: "0.82rem", color: "var(--color-text-secondary)", lineHeight: 1.6, margin: 0 }}>
                                {log.query}
                              </p>
                              {isLowFaith && (
                                <div style={{ marginTop: "0.75rem", padding: "0.5rem 0.75rem", background: "hsla(0, 72%, 51%, 0.1)", borderRadius: "var(--radius-sm)", fontSize: "0.78rem", color: "var(--color-danger)" }}>
                                  ⚠️ Low faithfulness score ({(log.faithfulness * 100).toFixed(1)}%) — This query may have generated non-grounded content. Review and re-index relevant documents.
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
