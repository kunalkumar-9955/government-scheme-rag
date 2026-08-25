"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/store/authStore";
import { motion } from "framer-motion";

const NAV_ITEMS = [
  { href: "/dashboard", icon: "📊", label: "Overview" },
  { href: "/dashboard/chat", icon: "💬", label: "AI Assistant" },
  { href: "/dashboard/find-schemes", icon: "🎯", label: "Find Schemes" },
  { href: "/dashboard/schemes", icon: "🏛️", label: "Browse Schemes" },
  { href: "/dashboard/compare", icon: "⚖️", label: "Compare Schemes" },
  { href: "/dashboard/saved", icon: "⭐", label: "Saved Schemes" },
  { href: "/dashboard/sources", icon: "📚", label: "Official Sources" },
  { href: "/dashboard/profile", icon: "👤", label: "My Profile" },
  { href: "/dashboard/history", icon: "📋", label: "History" },
  { href: "/dashboard/settings", icon: "⚙️", label: "Settings" },
];

const ADMIN_ITEMS = [
  { href: "/admin", icon: "🛡️", label: "Admin Panel" },
  { href: "/admin/evaluation", icon: "🔬", label: "RAG Evaluation" },
  { href: "/admin/schemes", icon: "🏛️", label: "Manage Schemes" },
  { href: "/admin/documents", icon: "📁", label: "Documents" },
  { href: "/admin/rag", icon: "🧠", label: "RAG Inspector" },
  { href: "/admin/users", icon: "👥", label: "Users & Roles" },
  { href: "/admin/logs", icon: "📋", label: "Query Logs" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, user, logout, fetchMe } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace("/login");
    } else {
      fetchMe();
    }
  }, [isAuthenticated]);

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      {/* ── Sidebar ── */}
      <aside className="sidebar" style={{ display: "flex", flexDirection: "column" }}>
        {/* Logo */}
        <div
          style={{
            padding: "1.25rem 1rem",
            borderBottom: "1px solid var(--color-border)",
            display: "flex",
            alignItems: "center",
            gap: "0.6rem",
          }}
        >
          <span style={{ fontSize: "1.4rem" }}>🏛️</span>
          <span
            style={{
              fontFamily: "Space Grotesk",
              fontWeight: 700,
              fontSize: "0.95rem",
              background: "var(--gradient-primary)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            GovScheme AI
          </span>
        </div>

        {/* Main Nav */}
        <nav style={{ flex: 1, padding: "0.75rem 0.5rem", overflowY: "auto" }}>
          <p style={{ fontSize: "0.7rem", fontWeight: 600, color: "var(--color-text-muted)", padding: "0.5rem 0.75rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Main
          </p>
          {NAV_ITEMS.map((item) => {
            const isActive = pathname?.startsWith(item.href);
            return (
              <Link key={item.href} href={item.href} style={{ textDecoration: "none" }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.65rem",
                    padding: "0.6rem 0.75rem",
                    borderRadius: "var(--radius-md)",
                    marginBottom: "0.15rem",
                    fontSize: "0.875rem",
                    fontWeight: isActive ? 600 : 400,
                    color: isActive ? "var(--color-text-primary)" : "var(--color-text-secondary)",
                    background: isActive ? "var(--color-bg-overlay)" : "transparent",
                    borderLeft: isActive ? "2px solid var(--color-primary)" : "2px solid transparent",
                    transition: "all 0.15s ease",
                    cursor: "pointer",
                  }}
                >
                  <span style={{ fontSize: "1rem" }}>{item.icon}</span>
                  {item.label}
                </div>
              </Link>
            );
          })}

          {/* Admin Nav */}
          {user && (user.role === "ADMIN" || user.role === "SUPER_ADMIN") && (
            <>
              <p style={{ fontSize: "0.7rem", fontWeight: 600, color: "var(--color-text-muted)", padding: "1rem 0.75rem 0.5rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                Admin
              </p>
              {ADMIN_ITEMS.map((item) => {
                const isActive = pathname?.startsWith(item.href);
                return (
                  <Link key={item.href} href={item.href} style={{ textDecoration: "none" }}>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "0.65rem",
                        padding: "0.6rem 0.75rem",
                        borderRadius: "var(--radius-md)",
                        marginBottom: "0.15rem",
                        fontSize: "0.875rem",
                        fontWeight: isActive ? 600 : 400,
                        color: isActive ? "var(--color-text-primary)" : "var(--color-text-secondary)",
                        background: isActive ? "var(--color-bg-overlay)" : "transparent",
                        borderLeft: isActive ? "2px solid var(--color-accent)" : "2px solid transparent",
                        transition: "all 0.15s ease",
                        cursor: "pointer",
                      }}
                    >
                      <span style={{ fontSize: "1rem" }}>{item.icon}</span>
                      {item.label}
                    </div>
                  </Link>
                );
              })}
            </>
          )}
        </nav>

        {/* User Footer */}
        <div
          style={{
            padding: "0.75rem",
            borderTop: "1px solid var(--color-border)",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              padding: "0.6rem",
              borderRadius: "var(--radius-md)",
              background: "var(--color-bg-elevated)",
            }}
          >
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: "50%",
                background: "var(--gradient-primary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "0.8rem",
                fontWeight: 600,
                flexShrink: 0,
              }}
            >
              {user?.email?.[0]?.toUpperCase() || "U"}
            </div>
            <div style={{ flex: 1, overflow: "hidden" }}>
              <p style={{ fontSize: "0.78rem", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {user?.email}
              </p>
              <p style={{ fontSize: "0.68rem", color: "var(--color-text-muted)" }}>{user?.role}</p>
            </div>
            <button onClick={handleLogout} className="btn-ghost" style={{ padding: "0.25rem 0.5rem", fontSize: "0.8rem" }}>
              →
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main Content ── */}
      <div style={{ flex: 1, overflow: "auto", background: "var(--color-bg-base)" }}>
        {children}
      </div>
    </div>
  );
}
