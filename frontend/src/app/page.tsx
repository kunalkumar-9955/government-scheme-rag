"use client";

import Link from "next/link";
import { motion, Variants } from "framer-motion";

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 30 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" } },
};

const stagger: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12 } },
};

const features = [
  {
    icon: "🔍",
    title: "Smart Scheme Discovery",
    desc: "Ask in plain language. Our AI searches official government documents to find schemes relevant to your situation.",
  },
  {
    icon: "✅",
    title: "Eligibility Evaluation",
    desc: "Upload your profile once. Get instant eligibility assessment with matched criteria and confidence scores.",
  },
  {
    icon: "📄",
    title: "Source Citations",
    desc: "Every answer is backed by exact references from official government documents. No hallucinations.",
  },
  {
    icon: "💬",
    title: "AI Chat Interface",
    desc: "Chat naturally in any language. The AI understands context and remembers your conversation history.",
  },
  {
    icon: "🛡️",
    title: "Trustworthy & Verified",
    desc: "Built on RAG technology — only answers from official Ministry documents. Evidence-first, always.",
  },
  {
    icon: "📊",
    title: "Personalized Dashboard",
    desc: "Track your eligibility results, conversation history, and recommended schemes in one place.",
  },
];

const stats = [
  { label: "Government Schemes", value: "1,500+" },
  { label: "Ministries Covered", value: "40+" },
  { label: "States & UTs", value: "36" },
  { label: "Languages Supported", value: "10+" },
];

export default function HomePage() {
  return (
    <main style={{ background: "var(--color-bg-base)", minHeight: "100vh" }}>
      {/* ── Navigation ── */}
      <nav
        className="glass"
        style={{
          position: "sticky",
          top: 0,
          zIndex: 50,
          padding: "1rem 2rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <span style={{ fontSize: "1.5rem" }}>🏛️</span>
          <span
            style={{
              fontFamily: "Space Grotesk",
              fontWeight: 700,
              fontSize: "1.05rem",
              background: "var(--gradient-primary)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            GovScheme AI
          </span>
        </div>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <Link href="/login">
            <button className="btn-secondary" style={{ padding: "0.5rem 1.25rem" }}>
              Sign In
            </button>
          </Link>
          <Link href="/register">
            <button className="btn-primary">Get Started</button>
          </Link>
        </div>
      </nav>

      {/* ── Hero Section ── */}
      <section
        style={{
          position: "relative",
          padding: "6rem 2rem 5rem",
          textAlign: "center",
          overflow: "hidden",
        }}
      >
        {/* Background orbs */}
        <div
          style={{
            position: "absolute",
            top: "-10%",
            left: "50%",
            transform: "translateX(-50%)",
            width: "800px",
            height: "400px",
            background:
              "radial-gradient(ellipse, hsla(230, 85%, 60%, 0.12) 0%, transparent 70%)",
            pointerEvents: "none",
          }}
        />
        <div
          style={{
            position: "absolute",
            bottom: "0",
            left: "10%",
            width: "400px",
            height: "300px",
            background:
              "radial-gradient(ellipse, hsla(160, 80%, 45%, 0.08) 0%, transparent 70%)",
            pointerEvents: "none",
          }}
        />

        <motion.div
          variants={stagger}
          initial="hidden"
          animate="show"
          style={{ position: "relative", maxWidth: "900px", margin: "0 auto" }}
        >
          <motion.div variants={fadeUp}>
            <span
              className="badge badge-primary"
              style={{ marginBottom: "1.5rem", display: "inline-flex", fontSize: "0.75rem" }}
            >
              🇮🇳 Powered by Official Government Documents
            </span>
          </motion.div>

          <motion.h1
            variants={fadeUp}
            style={{
              fontSize: "clamp(2.5rem, 5vw, 4.5rem)",
              fontWeight: 800,
              lineHeight: 1.1,
              marginBottom: "1.5rem",
            }}
          >
            Discover Government Schemes{" "}
            <span
              style={{
                background: "var(--gradient-primary)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              Made for You
            </span>
          </motion.h1>

          <motion.p
            variants={fadeUp}
            style={{
              fontSize: "1.2rem",
              color: "var(--color-text-secondary)",
              maxWidth: "650px",
              margin: "0 auto 2.5rem",
              lineHeight: 1.7,
            }}
          >
            AI-powered platform that reads official government documents, understands your
            situation, and tells you exactly which schemes you qualify for — with evidence and
            source citations.
          </motion.p>

          <motion.div
            variants={fadeUp}
            style={{ display: "flex", gap: "1rem", justifyContent: "center", flexWrap: "wrap" }}
          >
            <Link href="/register">
              <button className="btn-primary glow-pulse" style={{ fontSize: "1rem", padding: "0.8rem 2rem" }}>
                🚀 Check Your Eligibility — Free
              </button>
            </Link>
            <Link href="/schemes">
              <button className="btn-secondary" style={{ fontSize: "1rem", padding: "0.8rem 2rem" }}>
                Browse All Schemes
              </button>
            </Link>
          </motion.div>
        </motion.div>
      </section>

      {/* ── Stats Bar ── */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        style={{
          background: "var(--color-bg-surface)",
          borderTop: "1px solid var(--color-border)",
          borderBottom: "1px solid var(--color-border)",
          padding: "2rem",
        }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "2rem",
            maxWidth: "1000px",
            margin: "0 auto",
            textAlign: "center",
          }}
        >
          {stats.map((s) => (
            <div key={s.label}>
              <div
                style={{
                  fontSize: "2.2rem",
                  fontWeight: 800,
                  fontFamily: "Space Grotesk",
                  background: "var(--gradient-primary)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                }}
              >
                {s.value}
              </div>
              <div style={{ fontSize: "0.85rem", color: "var(--color-text-muted)", marginTop: "0.25rem" }}>
                {s.label}
              </div>
            </div>
          ))}
        </div>
      </motion.section>

      {/* ── Features Grid ── */}
      <section style={{ padding: "5rem 2rem", maxWidth: "1200px", margin: "0 auto" }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          style={{ textAlign: "center", marginBottom: "3rem" }}
        >
          <h2 style={{ fontSize: "2.2rem", marginBottom: "1rem" }}>
            Not Just Another Chatbot
          </h2>
          <p style={{ color: "var(--color-text-secondary)", fontSize: "1.05rem", maxWidth: "550px", margin: "0 auto" }}>
            Purpose-built for India's government scheme ecosystem with advanced RAG technology.
          </p>
        </motion.div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
            gap: "1.5rem",
          }}
        >
          {features.map((feature, i) => (
            <motion.div
              key={feature.title}
              className="card"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
              style={{ cursor: "default" }}
              whileHover={{ borderColor: "var(--color-primary)", y: -2 }}
            >
              <div style={{ fontSize: "2rem", marginBottom: "0.75rem" }}>{feature.icon}</div>
              <h3 style={{ fontSize: "1.1rem", marginBottom: "0.5rem" }}>{feature.title}</h3>
              <p style={{ color: "var(--color-text-secondary)", fontSize: "0.9rem", lineHeight: 1.6 }}>
                {feature.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── CTA Section ── */}
      <section
        style={{
          background: "var(--color-bg-surface)",
          borderTop: "1px solid var(--color-border)",
          padding: "5rem 2rem",
          textAlign: "center",
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <h2 style={{ fontSize: "2.2rem", marginBottom: "1rem" }}>
            Start Getting the Benefits You Deserve
          </h2>
          <p style={{ color: "var(--color-text-secondary)", marginBottom: "2rem", fontSize: "1.05rem" }}>
            Complete your profile in 5 minutes and see every scheme you qualify for.
          </p>
          <Link href="/register">
            <button className="btn-primary glow-pulse" style={{ fontSize: "1rem", padding: "0.9rem 2.5rem" }}>
              Create Free Account →
            </button>
          </Link>
        </motion.div>
      </section>

      {/* ── Footer ── */}
      <footer
        style={{
          padding: "2rem",
          textAlign: "center",
          borderTop: "1px solid var(--color-border)",
          color: "var(--color-text-muted)",
          fontSize: "0.85rem",
        }}
      >
        <p>© 2026 Government Scheme AI Assistant. Information sourced from official government documents.</p>
        <p style={{ marginTop: "0.5rem" }}>
          Always verify scheme details at{" "}
          <a
            href="https://myscheme.gov.in"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: "var(--color-primary-light)" }}
          >
            myscheme.gov.in
          </a>
        </p>
      </footer>
    </main>
  );
}
