"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/store/authStore";

const ADMIN_NAV = [
  { href: "/admin", icon: "📊", label: "Dashboard & RAG" },
  { href: "/admin/evaluation", icon: "🔬", label: "RAG Evaluation" },
  { href: "/admin/schemes", icon: "🏛️", label: "Schemes" },
  { href: "/admin/documents", icon: "📁", label: "Documents" },
  { href: "/admin/rag", icon: "🧠", label: "RAG & Chunks" },
  { href: "/admin/users", icon: "👥", label: "Users & Roles" },
  { href: "/admin/logs", icon: "📋", label: "Query Logs" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace("/login");
    } else if (user && user.role !== "ADMIN" && user.role !== "SUPER_ADMIN") {
      router.replace("/dashboard");
    }
  }, [isAuthenticated, user, router]);

  if (!isAuthenticated || (user && user.role !== "ADMIN" && user.role !== "SUPER_ADMIN")) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
        <div className="spinner" style={{ width: 36, height: 36 }} />
      </div>
    );
  }

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", background: "var(--color-bg-base)" }}>
      {/* ── Admin Sidebar ── */}
      <aside className="sidebar" style={{ display: "flex", flexDirection: "column", width: "260px" }}>
        {/* Admin Brand */}
        <div
          style={{
            padding: "1.25rem 1rem",
            borderBottom: "1px solid var(--color-border)",
            display: "flex",
            alignItems: "center",
            gap: "0.6rem",
          }}
        >
          <span style={{ fontSize: "1.3rem" }}>🛡️</span>
          <div>
            <span
              style={{
                fontFamily: "Space Grotesk",
                fontWeight: 700,
                fontSize: "0.95rem",
                color: "var(--color-text-primary)",
                display: "block",
              }}
            >
              GovScheme Admin
            </span>
            <span style={{ fontSize: "0.7rem", color: "var(--color-primary)", fontWeight: 600 }}>
              {user?.role === "SUPER_ADMIN" ? "SUPER ADMIN" : "ADMINISTRATOR"}
            </span>
          </div>
        </div>

        {/* Navigation */}
        <nav style={{ flex: 1, padding: "1rem 0.5rem", display: "flex", flexDirection: "column", gap: "0.3rem" }}>
          {ADMIN_NAV.map((item) => {
            const isActive = pathname === item.href || (item.href !== "/admin" && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`nav-item ${isActive ? "active" : ""}`}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                  padding: "0.65rem 0.85rem",
                  borderRadius: "var(--radius-md)",
                  fontSize: "0.85rem",
                  fontWeight: isActive ? 600 : 500,
                  color: isActive ? "var(--color-text-primary)" : "var(--color-text-secondary)",
                  background: isActive ? "var(--color-bg-overlay)" : "transparent",
                  textDecoration: "none",
                  border: isActive ? "1px solid var(--color-border)" : "1px solid transparent",
                }}
              >
                <span style={{ fontSize: "1rem" }}>{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Back to citizen portal */}
        <div style={{ padding: "1rem 0.75rem", borderTop: "1px solid var(--color-border)" }}>
          <Link
            href="/dashboard"
            className="btn-ghost"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              fontSize: "0.8rem",
              width: "100%",
              justifyContent: "center",
              textDecoration: "none",
              marginBottom: "0.5rem",
            }}
          >
            ← Citizen Portal
          </Link>
          <div style={{ fontSize: "0.72rem", color: "var(--color-text-muted)", textAlign: "center" }}>
            Logged in as {user?.email}
          </div>
        </div>
      </aside>

      {/* ── Main Admin Content ── */}
      <main style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column" }}>
        {children}
      </main>
    </div>
  );
}
