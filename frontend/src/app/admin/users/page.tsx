"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { usersAdminApi } from "@/lib/api/endpoints";

const ROLES = ["CITIZEN", "ADMIN", "SUPER_ADMIN"];

const ROLE_BADGE_CLASS: Record<string, string> = {
  CITIZEN: "badge",
  ADMIN: "badge badge-primary",
  SUPER_ADMIN: "badge badge-success",
};

export default function AdminUsersPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [newRole, setNewRole] = useState("");

  const { data: usersRes, isLoading, refetch } = useQuery({
    queryKey: ["adminUsersList", page],
    queryFn: () => usersAdminApi.listUsers({ page, page_size: 30 }),
    refetchInterval: 30000,
  });

  const users: any[] = (usersRes?.data?.data as any)?.results || (usersRes?.data?.data as any[]) || [];
  const totalCount = (usersRes?.data?.data as any)?.count || users.length;

  const roleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      usersAdminApi.changeRole(userId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminUsersList"] });
      setSelectedUserId(null);
      setNewRole("");
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: (userId: string) => usersAdminApi.deactivateUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminUsersList"] });
    },
  });

  const filteredUsers = search.trim()
    ? users.filter(
        (u: any) =>
          u.email?.toLowerCase().includes(search.toLowerCase()) ||
          u.role?.toLowerCase().includes(search.toLowerCase())
      )
    : users;

  const selectedUser = selectedUserId ? users.find((u: any) => u.id === selectedUserId) : null;

  return (
    <div style={{ padding: "2rem", height: "100%", overflowY: "auto" }}>
      {/* Header */}
      <div style={{ marginBottom: "2rem", display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "0 0 0.4rem" }}>
            👥 User Access & Role Management
          </h1>
          <p style={{ color: "var(--color-text-secondary)", fontSize: "0.9rem" }}>
            Manage citizen accounts, grant administrator roles, and deactivate suspicious accounts. All role changes are audited.
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <span className="badge badge-success">{totalCount} Total Users</span>
          <button onClick={() => refetch()} className="btn-secondary" style={{ fontSize: "0.82rem" }}>
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* Security Notice Banner */}
      <div
        style={{
          padding: "0.85rem 1.25rem",
          borderRadius: "var(--radius-md)",
          marginBottom: "1.5rem",
          background: "hsla(222, 72%, 50%, 0.08)",
          border: "1px solid hsla(222, 72%, 50%, 0.25)",
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
          fontSize: "0.82rem",
          color: "var(--color-text-secondary)",
        }}
      >
        <span style={{ fontSize: "1.1rem" }}>🔒</span>
        <span>
          <strong>Security Policy:</strong> All role promotions require Super Admin privilege. Role changes are logged in the system audit trail. No direct database manipulation from this interface.
        </span>
      </div>

      {/* Search */}
      <div style={{ marginBottom: "1.25rem" }}>
        <input
          type="text"
          placeholder="🔍 Search by email or role..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input-field"
          style={{ maxWidth: "380px" }}
        />
      </div>

      {/* Users Table */}
      <div className="card-elevated" style={{ borderRadius: "var(--radius-xl)", overflow: "hidden", border: "1px solid var(--color-border)" }}>
        {isLoading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: "3rem" }}>
            <div className="spinner" />
          </div>
        ) : filteredUsers.length === 0 ? (
          <div style={{ padding: "3rem", textAlign: "center" }}>
            <span style={{ fontSize: "2rem", display: "block", marginBottom: "0.5rem" }}>👥</span>
            <p style={{ color: "var(--color-text-muted)", fontSize: "0.88rem" }}>No users found.</p>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--color-border)", textAlign: "left", background: "var(--color-bg-overlay)", color: "var(--color-text-muted)" }}>
                  <th style={{ padding: "0.85rem 1rem" }}>Email</th>
                  <th style={{ padding: "0.85rem 1rem" }}>Role</th>
                  <th style={{ padding: "0.85rem 1rem" }}>Status</th>
                  <th style={{ padding: "0.85rem 1rem" }}>Verified</th>
                  <th style={{ padding: "0.85rem 1rem" }}>Joined</th>
                  <th style={{ padding: "0.85rem 1rem" }}>Profile</th>
                  <th style={{ padding: "0.85rem 1rem", textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((user: any) => (
                  <tr key={user.id} style={{ borderBottom: "1px solid var(--color-border-subtle)" }}>
                    <td style={{ padding: "0.85rem 1rem", fontWeight: 600, color: "var(--color-text-primary)" }}>
                      {user.email}
                    </td>
                    <td style={{ padding: "0.85rem 1rem" }}>
                      <span className={ROLE_BADGE_CLASS[user.role] || "badge"}>
                        {user.role}
                      </span>
                    </td>
                    <td style={{ padding: "0.85rem 1rem" }}>
                      <span className={user.is_active ? "badge badge-success" : "badge badge-danger"}>
                        {user.is_active ? "Active" : "Deactivated"}
                      </span>
                    </td>
                    <td style={{ padding: "0.85rem 1rem" }}>
                      {user.is_email_verified ? (
                        <span style={{ color: "var(--color-success)", fontWeight: 600, fontSize: "0.8rem" }}>✓ Verified</span>
                      ) : (
                        <span style={{ color: "var(--color-danger)", fontSize: "0.8rem" }}>✗ Unverified</span>
                      )}
                    </td>
                    <td style={{ padding: "0.85rem 1rem", color: "var(--color-text-muted)", whiteSpace: "nowrap" }}>
                      {user.date_joined
                        ? new Date(user.date_joined).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })
                        : "—"}
                    </td>
                    <td style={{ padding: "0.85rem 1rem", color: "var(--color-text-secondary)" }}>
                      {user.profile?.full_name || (
                        <span style={{ color: "var(--color-text-muted)" }}>Not Set</span>
                      )}
                    </td>
                    <td style={{ padding: "0.85rem 1rem", textAlign: "right" }}>
                      <div style={{ display: "flex", gap: "0.4rem", justifyContent: "flex-end" }}>
                        <button
                          onClick={() => {
                            setSelectedUserId(user.id);
                            setNewRole(user.role);
                          }}
                          className="btn-secondary"
                          style={{ fontSize: "0.75rem", padding: "0.25rem 0.5rem" }}
                        >
                          Change Role
                        </button>
                        {user.is_active && (
                          <button
                            onClick={() => {
                              if (confirm(`Deactivate account for ${user.email}?`)) {
                                deactivateMutation.mutate(user.id);
                              }
                            }}
                            disabled={deactivateMutation.isPending}
                            className="btn-ghost"
                            style={{ fontSize: "0.75rem", padding: "0.25rem 0.5rem", color: "var(--color-danger)" }}
                          >
                            Deactivate
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      <div style={{ display: "flex", justifyContent: "center", gap: "0.5rem", marginTop: "1.5rem" }}>
        <button
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page === 1}
          className="btn-secondary"
          style={{ padding: "0.4rem 0.9rem", fontSize: "0.82rem" }}
        >
          ← Prev
        </button>
        <span style={{ padding: "0.4rem 0.9rem", fontSize: "0.82rem", color: "var(--color-text-muted)" }}>
          Page {page} · {totalCount} total users
        </span>
        <button
          onClick={() => setPage((p) => p + 1)}
          disabled={users.length < 30}
          className="btn-secondary"
          style={{ padding: "0.4rem 0.9rem", fontSize: "0.82rem" }}
        >
          Next →
        </button>
      </div>

      {/* Change Role Modal */}
      {selectedUserId && selectedUser && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "hsla(222, 47%, 5%, 0.85)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
            padding: "1.5rem",
            backdropFilter: "blur(4px)",
          }}
          onClick={() => setSelectedUserId(null)}
        >
          <div
            className="card-elevated"
            style={{ maxWidth: "440px", width: "100%", borderRadius: "var(--radius-xl)", padding: "2rem" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem" }}>
              <h3 style={{ fontSize: "1.1rem", fontWeight: 700, margin: 0 }}>Change User Role</h3>
              <button onClick={() => setSelectedUserId(null)} className="btn-ghost">✕</button>
            </div>

            <div style={{ background: "var(--color-bg-overlay)", padding: "0.85rem 1rem", borderRadius: "var(--radius-md)", marginBottom: "1.25rem" }}>
              <p style={{ margin: 0, fontSize: "0.85rem" }}>
                <strong>{selectedUser.email}</strong>
              </p>
              <p style={{ margin: "0.2rem 0 0", fontSize: "0.78rem", color: "var(--color-text-muted)" }}>
                Current Role: {selectedUser.role}
              </p>
            </div>

            <div style={{ marginBottom: "1.25rem" }}>
              <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: "0.4rem" }}>
                Assign New Role
              </label>
              <select
                value={newRole}
                onChange={(e) => setNewRole(e.target.value)}
                className="input-field"
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>

            <div style={{ padding: "0.75rem 1rem", background: "hsla(38, 92%, 50%, 0.08)", borderRadius: "var(--radius-md)", marginBottom: "1.25rem", fontSize: "0.78rem", color: "var(--color-accent)", border: "1px solid hsla(38, 92%, 50%, 0.25)" }}>
              ⚠️ Role changes are permanent audit-log actions. Granting ADMIN or SUPER_ADMIN access gives full system privileges.
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
              <button onClick={() => setSelectedUserId(null)} className="btn-secondary">Cancel</button>
              <button
                onClick={() => roleMutation.mutate({ userId: selectedUserId, role: newRole })}
                disabled={roleMutation.isPending || newRole === selectedUser.role}
                className="btn-primary"
              >
                {roleMutation.isPending ? "Saving..." : "Confirm Role Change"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
