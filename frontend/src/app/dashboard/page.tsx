"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { motion } from "framer-motion";
import { useAuthStore } from "@/store/authStore";
import { userApi, schemesApi } from "@/lib/api/endpoints";

export default function DashboardOverviewPage() {
  const { user } = useAuthStore();

  const { data: profileRes, isLoading: isLoadingProfile } = useQuery({
    queryKey: ["userProfile"],
    queryFn: () => userApi.getMyProfile(),
    staleTime: 5 * 60 * 1000,
  });

  const { data: statsRes } = useQuery({
    queryKey: ["schemeStats"],
    queryFn: () => schemesApi.getStats(),
    staleTime: 10 * 60 * 1000,
  });

  const { data: schemesRes } = useQuery({
    queryKey: ["popularSchemes"],
    queryFn: () => schemesApi.listSchemes({ page_size: 6 }),
    staleTime: 5 * 60 * 1000,
  });

  const profile = profileRes?.data?.data;
  const stats = statsRes?.data?.data;
  const popularSchemes = schemesRes?.data?.results || [];

  const completionScore = profile?.profile_completion_score || 0;

  return (
    <div style={{ padding: "2rem", height: "100%", overflowY: "auto" }}>
      {/* Welcome Banner */}
      <div
        className="card-elevated"
        style={{
          borderRadius: "var(--radius-xl)",
          padding: "2rem",
          marginBottom: "2rem",
          background: "linear-gradient(135deg, hsla(230, 85%, 60%, 0.15) 0%, hsla(270, 70%, 55%, 0.08) 100%)",
          border: "1px solid var(--color-border)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1.5rem",
        }}
      >
        <div style={{ maxWidth: "600px" }}>
          <span className="badge badge-primary" style={{ marginBottom: "0.5rem" }}>
            🇮🇳 Government Scheme AI Platform
          </span>
          <h1 style={{ fontSize: "1.85rem", fontWeight: 700, margin: "0.25rem 0 0.5rem", color: "var(--color-text-primary)" }}>
            Welcome back, {profile?.full_name || user?.email?.split("@")[0] || "Citizen"}!
          </h1>
          <p style={{ color: "var(--color-text-secondary)", fontSize: "0.92rem", lineHeight: 1.6 }}>
            Your personal portal for exploring official central and state government welfare schemes, evaluating eligibility with deterministic rules, and querying verified documents with AI.
          </p>
        </div>

        {/* Profile Completion Widget */}
        <div
          style={{
            background: "var(--color-bg-overlay)",
            padding: "1.25rem 1.5rem",
            borderRadius: "var(--radius-lg)",
            border: "1px solid var(--color-border)",
            minWidth: "220px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.4rem" }}>
            <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--color-text-secondary)" }}>
              Profile Completion
            </span>
            <span style={{ fontSize: "0.85rem", fontWeight: 700, color: completionScore > 75 ? "var(--color-success)" : "var(--color-accent)" }}>
              {completionScore}%
            </span>
          </div>
          <div
            style={{
              height: 8,
              background: "var(--color-bg-base)",
              borderRadius: 4,
              overflow: "hidden",
              marginBottom: "0.75rem",
            }}
          >
            <div
              style={{
                width: `${completionScore}%`,
                height: "100%",
                background: "var(--gradient-primary)",
                borderRadius: 4,
              }}
            />
          </div>
          <Link
            href="/dashboard/profile"
            style={{
              fontSize: "0.75rem",
              color: "var(--color-primary)",
              textDecoration: "underline",
              display: "block",
              textAlign: "right",
            }}
          >
            {completionScore < 100 ? "Complete Profile →" : "View Profile →"}
          </Link>
        </div>
      </div>

      {/* Quick Actions Grid */}
      <div style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.2rem", fontWeight: 700, marginBottom: "1rem", color: "var(--color-text-primary)" }}>
          Quick Services
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "1rem" }}>
          <Link
            href="/dashboard/chat"
            className="card"
            style={{
              padding: "1.25rem",
              borderRadius: "var(--radius-lg)",
              border: "1px solid var(--color-border)",
              textDecoration: "none",
              display: "flex",
              flexDirection: "column",
              gap: "0.5rem",
              transition: "all 0.15s ease",
            }}
          >
            <span style={{ fontSize: "1.8rem" }}>💬</span>
            <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: 0, color: "var(--color-text-primary)" }}>
              AI Scheme Assistant
            </h3>
            <p style={{ fontSize: "0.82rem", color: "var(--color-text-secondary)", margin: 0, lineHeight: 1.5 }}>
              Ask natural language questions and get grounded answers with official citations.
            </p>
          </Link>

          <Link
            href="/dashboard/find-schemes"
            className="card"
            style={{
              padding: "1.25rem",
              borderRadius: "var(--radius-lg)",
              border: "1px solid var(--color-border)",
              textDecoration: "none",
              display: "flex",
              flexDirection: "column",
              gap: "0.5rem",
              transition: "all 0.15s ease",
            }}
          >
            <span style={{ fontSize: "1.8rem" }}>🎯</span>
            <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: 0, color: "var(--color-text-primary)" }}>
              Find Schemes For Me
            </h3>
            <p style={{ fontSize: "0.82rem", color: "var(--color-text-secondary)", margin: 0, lineHeight: 1.5 }}>
              Enter your profile attributes and evaluate your eligibility across all schemes.
            </p>
          </Link>

          <Link
            href="/dashboard/schemes"
            className="card"
            style={{
              padding: "1.25rem",
              borderRadius: "var(--radius-lg)",
              border: "1px solid var(--color-border)",
              textDecoration: "none",
              display: "flex",
              flexDirection: "column",
              gap: "0.5rem",
              transition: "all 0.15s ease",
            }}
          >
            <span style={{ fontSize: "1.8rem" }}>🏛️</span>
            <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: 0, color: "var(--color-text-primary)" }}>
              Browse Schemes
            </h3>
            <p style={{ fontSize: "0.82rem", color: "var(--color-text-secondary)", margin: 0, lineHeight: 1.5 }}>
              Explore schemes filtered by ministry, state, category, and benefit type.
            </p>
          </Link>

          <Link
            href="/dashboard/compare"
            className="card"
            style={{
              padding: "1.25rem",
              borderRadius: "var(--radius-lg)",
              border: "1px solid var(--color-border)",
              textDecoration: "none",
              display: "flex",
              flexDirection: "column",
              gap: "0.5rem",
              transition: "all 0.15s ease",
            }}
          >
            <span style={{ fontSize: "1.8rem" }}>⚖️</span>
            <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: 0, color: "var(--color-text-primary)" }}>
              Compare Schemes
            </h3>
            <p style={{ fontSize: "0.82rem", color: "var(--color-text-secondary)", margin: 0, lineHeight: 1.5 }}>
              Side-by-side comparison of benefits, eligibility, and required paperwork.
            </p>
          </Link>
        </div>
      </div>

      {/* Platform Statistics */}
      {stats && (
        <div style={{ marginBottom: "2rem" }}>
          <h2 style={{ fontSize: "1.2rem", fontWeight: 700, marginBottom: "1rem", color: "var(--color-text-primary)" }}>
            Verified Scheme Database
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "1rem" }}>
            <div className="card" style={{ padding: "1rem", borderRadius: "var(--radius-md)", border: "1px solid var(--color-border)" }}>
              <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", textTransform: "uppercase" }}>Total Schemes</span>
              <h4 style={{ fontSize: "1.6rem", fontWeight: 700, margin: "0.2rem 0 0", color: "var(--color-primary)" }}>
                {stats.total_schemes || 0}
              </h4>
            </div>
            <div className="card" style={{ padding: "1rem", borderRadius: "var(--radius-md)", border: "1px solid var(--color-border)" }}>
              <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", textTransform: "uppercase" }}>Active Schemes</span>
              <h4 style={{ fontSize: "1.6rem", fontWeight: 700, margin: "0.2rem 0 0", color: "var(--color-success)" }}>
                {stats.active_schemes || 0}
              </h4>
            </div>
            <div className="card" style={{ padding: "1rem", borderRadius: "var(--radius-md)", border: "1px solid var(--color-border)" }}>
              <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", textTransform: "uppercase" }}>Central Sector</span>
              <h4 style={{ fontSize: "1.6rem", fontWeight: 700, margin: "0.2rem 0 0", color: "var(--color-accent)" }}>
                {stats.central_schemes || 0}
              </h4>
            </div>
            <div className="card" style={{ padding: "1rem", borderRadius: "var(--radius-md)", border: "1px solid var(--color-border)" }}>
              <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", textTransform: "uppercase" }}>Nodal Ministries</span>
              <h4 style={{ fontSize: "1.6rem", fontWeight: 700, margin: "0.2rem 0 0", color: "var(--color-text-primary)" }}>
                {stats.total_ministries || 0}
              </h4>
            </div>
          </div>
        </div>
      )}

      {/* Featured Government Schemes */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <h2 style={{ fontSize: "1.2rem", fontWeight: 700, margin: 0, color: "var(--color-text-primary)" }}>
            Featured Government Schemes
          </h2>
          <Link href="/dashboard/schemes" style={{ fontSize: "0.85rem", color: "var(--color-primary)", textDecoration: "underline" }}>
            View All Schemes →
          </Link>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1rem" }}>
          {popularSchemes.slice(0, 4).map((s: any) => (
            <div
              key={s.id}
              className="card-elevated"
              style={{
                padding: "1.25rem",
                borderRadius: "var(--radius-lg)",
                border: "1px solid var(--color-border)",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
              }}
            >
              <div>
                <div style={{ display: "flex", gap: "0.4rem", marginBottom: "0.5rem", flexWrap: "wrap" }}>
                  <span className="badge badge-primary">{s.category?.name || "General"}</span>
                  {s.scheme_type && <span className="badge badge-accent">{s.scheme_type.replace("_", " ")}</span>}
                </div>
                <h3 style={{ fontSize: "1.05rem", fontWeight: 700, margin: "0 0 0.35rem", color: "var(--color-text-primary)" }}>
                  {s.name}
                </h3>
                <p style={{ fontSize: "0.82rem", color: "var(--color-text-secondary)", lineHeight: 1.5, marginBottom: "0.75rem" }}>
                  {s.description ? `${s.description.slice(0, 140)}...` : "Official Government welfare initiative."}
                </p>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid var(--color-border)", paddingTop: "0.75rem" }}>
                <Link
                  href={`/dashboard/chat?query=Tell me about ${encodeURIComponent(s.name)}`}
                  className="btn-ghost"
                  style={{ fontSize: "0.78rem", textDecoration: "none" }}
                >
                  💬 Ask AI Assistant
                </Link>
                <Link
                  href={`/dashboard/schemes/${s.id}`}
                  className="btn-primary"
                  style={{ fontSize: "0.78rem", padding: "0.4rem 0.8rem", textDecoration: "none" }}
                >
                  View Details →
                </Link>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
