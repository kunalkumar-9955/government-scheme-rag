"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import Link from "next/link";
import { chatApi, eligibilityApi } from "@/lib/api/endpoints";

export default function HistoryPage() {
  const { data: convData, isLoading: isLoadingConvs } = useQuery({
    queryKey: ["conversationsHistory"],
    queryFn: () => chatApi.listConversations(),
  });

  const { data: eligData, isLoading: isLoadingElig } = useQuery({
    queryKey: ["eligibilityHistory"],
    queryFn: () => eligibilityApi.getResults(),
  });

  const conversations = convData?.data?.data || [];
  const evaluations = ((eligData?.data?.data as any)?.results || []) as any[];

  return (
    <div style={{ padding: "2rem", maxWidth: "900px", margin: "0 auto" }}>
      <div style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "1.75rem", marginBottom: "0.5rem" }}>Activity & History</h1>
        <p style={{ color: "var(--color-text-secondary)" }}>
          Review your past AI conversations and eligibility evaluation records.
        </p>
      </div>

      {/* Conversations Section */}
      <section style={{ marginBottom: "2.5rem" }}>
        <h2 style={{ fontSize: "1.15rem", fontWeight: 600, marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
          💬 Conversation History
        </h2>

        {isLoadingConvs ? (
          <div className="card" style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <div className="spinner" style={{ width: 18, height: 18 }} />
            <span style={{ color: "var(--color-text-muted)" }}>Loading conversations...</span>
          </div>
        ) : conversations.length === 0 ? (
          <div className="card" style={{ textAlign: "center", padding: "2rem", color: "var(--color-text-muted)" }}>
            <p style={{ fontSize: "1.75rem", margin: "0 0 0.5rem 0" }}>💭</p>
            <p style={{ margin: 0 }}>No conversations yet.</p>
            <Link href="/dashboard/chat" style={{ marginTop: "0.75rem", display: "inline-block" }}>
              <button className="btn-primary" style={{ fontSize: "0.85rem", padding: "0.5rem 1rem" }}>
                Start a New Chat
              </button>
            </Link>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {conversations.map((conv: any, i: number) => (
              <motion.div
                key={conv.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="card"
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "1rem 1.25rem",
                }}
              >
                <div>
                  <h3 style={{ fontSize: "0.95rem", margin: "0 0 0.25rem 0" }}>{conv.title || "Conversation"}</h3>
                  <p style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", margin: 0 }}>
                    {conv.message_count || 0} messages • Last active: {new Date(conv.updated_at || conv.created_at).toLocaleDateString()}
                  </p>
                </div>
                <Link href="/dashboard/chat">
                  <button className="btn-secondary" style={{ fontSize: "0.8rem", padding: "0.4rem 0.8rem" }}>
                    Continue →
                  </button>
                </Link>
              </motion.div>
            ))}
          </div>
        )}
      </section>

      {/* Eligibility History Section */}
      <section>
        <h2 style={{ fontSize: "1.15rem", fontWeight: 600, marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
          📊 Eligibility Evaluation History
        </h2>

        {isLoadingElig ? (
          <div className="card" style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <div className="spinner" style={{ width: 18, height: 18 }} />
            <span style={{ color: "var(--color-text-muted)" }}>Loading evaluations...</span>
          </div>
        ) : evaluations.length === 0 ? (
          <div className="card" style={{ textAlign: "center", padding: "2rem", color: "var(--color-text-muted)" }}>
            <p style={{ fontSize: "1.75rem", margin: "0 0 0.5rem 0" }}>📋</p>
            <p style={{ margin: 0 }}>No eligibility evaluations recorded yet.</p>
            <p style={{ fontSize: "0.8rem", marginTop: "0.5rem" }}>
              Complete your profile and use the AI assistant to check scheme qualifications.
            </p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {evaluations.map((evalItem: any) => (
              <div key={evalItem.id} className="card" style={{ padding: "1rem 1.25rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <h3 style={{ fontSize: "0.95rem", margin: 0 }}>{evalItem.scheme_name}</h3>
                  <span className={`verdict-${evalItem.verdict} badge`}>{evalItem.verdict}</span>
                </div>
                <p style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginTop: "0.5rem" }}>
                  {evalItem.explanation_summary}
                </p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
