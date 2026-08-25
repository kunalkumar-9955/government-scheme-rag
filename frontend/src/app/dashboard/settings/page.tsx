"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion } from "framer-motion";
import { authApi } from "@/lib/api/endpoints";
import { useAuthStore } from "@/store/authStore";

const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, "Current password is required"),
    new_password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .regex(/[A-Z]/, "Must contain an uppercase letter")
      .regex(/[0-9]/, "Must contain a number"),
    new_password_confirm: z.string().min(1, "Please confirm your new password"),
  })
  .refine((d) => d.new_password === d.new_password_confirm, {
    message: "New passwords do not match",
    path: ["new_password_confirm"],
  });

type ChangePasswordForm = z.infer<typeof changePasswordSchema>;

export default function SettingsPage() {
  const { user } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ChangePasswordForm>({
    resolver: zodResolver(changePasswordSchema),
  });

  const onSubmit = async (data: ChangePasswordForm) => {
    setIsLoading(true);
    setFeedback(null);
    try {
      const res = await authApi.changePassword(data);
      setFeedback({
        type: "success",
        text: res.data.message || "Password changed successfully!",
      });
      reset();
    } catch (err: any) {
      setFeedback({
        type: "error",
        text: err.response?.data?.error?.message || "Failed to update password. Check your current password.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ padding: "2rem", maxWidth: "700px", margin: "0 auto" }}>
      <div style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "1.75rem", marginBottom: "0.5rem" }}>Account Settings</h1>
        <p style={{ color: "var(--color-text-secondary)" }}>
          Manage your credentials, security preferences, and account details.
        </p>
      </div>

      {/* Account Info Card */}
      <section className="card" style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
          🛡️ Account Information
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
          <div>
            <p style={{ fontSize: "0.8rem", color: "var(--color-text-muted)", margin: 0 }}>Registered Email</p>
            <p style={{ fontSize: "0.95rem", fontWeight: 600, marginTop: "0.25rem" }}>{user?.email || "—"}</p>
          </div>
          <div>
            <p style={{ fontSize: "0.8rem", color: "var(--color-text-muted)", margin: 0 }}>Account Role</p>
            <div style={{ marginTop: "0.25rem" }}>
              <span className={`badge ${user?.role === "SUPER_ADMIN" ? "badge-error" : user?.role === "ADMIN" ? "badge-warning" : "badge-primary"}`}>
                {user?.role || "CITIZEN"}
              </span>
            </div>
          </div>
          <div>
            <p style={{ fontSize: "0.8rem", color: "var(--color-text-muted)", margin: 0 }}>Email Verification Status</p>
            <div style={{ marginTop: "0.25rem" }}>
              {user?.is_email_verified ? (
                <span className="badge badge-success">Verified</span>
              ) : (
                <span className="badge badge-warning">Unverified</span>
              )}
            </div>
          </div>
          <div>
            <p style={{ fontSize: "0.8rem", color: "var(--color-text-muted)", margin: 0 }}>Account ID</p>
            <p style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", fontFamily: "monospace", marginTop: "0.25rem" }}>
              {user?.id ? `${user.id.slice(0, 13)}...` : "—"}
            </p>
          </div>
        </div>
      </section>

      {/* Change Password Card */}
      <section className="card-elevated">
        <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
          🔑 Change Password
        </h2>

        {feedback && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            style={{
              padding: "0.75rem 1rem",
              borderRadius: "var(--radius-md)",
              fontSize: "0.875rem",
              marginBottom: "1.25rem",
              background: feedback.type === "success" ? "hsla(145, 65%, 45%, 0.12)" : "hsla(0, 75%, 60%, 0.1)",
              border: feedback.type === "success" ? "1px solid hsla(145, 65%, 45%, 0.25)" : "1px solid hsla(0, 75%, 60%, 0.25)",
              color: feedback.type === "success" ? "var(--color-success)" : "var(--color-error)",
            }}
          >
            {feedback.type === "success" ? "✅" : "⚠️"} {feedback.text}
          </motion.div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div>
            <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 500, marginBottom: "0.4rem" }}>
              Current Password
            </label>
            <input
              {...register("current_password")}
              type="password"
              className="input-field"
              placeholder="Enter your current password"
            />
            {errors.current_password && (
              <p style={{ color: "var(--color-error)", fontSize: "0.8rem", marginTop: "0.25rem" }}>
                {errors.current_password.message}
              </p>
            )}
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 500, marginBottom: "0.4rem" }}>
              New Password
            </label>
            <input
              {...register("new_password")}
              type="password"
              className="input-field"
              placeholder="Min 8 characters with numbers & uppercase"
            />
            {errors.new_password && (
              <p style={{ color: "var(--color-error)", fontSize: "0.8rem", marginTop: "0.25rem" }}>
                {errors.new_password.message}
              </p>
            )}
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 500, marginBottom: "0.4rem" }}>
              Confirm New Password
            </label>
            <input
              {...register("new_password_confirm")}
              type="password"
              className="input-field"
              placeholder="Repeat your new password"
            />
            {errors.new_password_confirm && (
              <p style={{ color: "var(--color-error)", fontSize: "0.8rem", marginTop: "0.25rem" }}>
                {errors.new_password_confirm.message}
              </p>
            )}
          </div>

          <div>
            <button
              type="submit"
              className="btn-primary"
              disabled={isLoading}
              style={{ padding: "0.75rem 1.75rem", fontSize: "0.9rem" }}
            >
              {isLoading ? (
                <>
                  <div className="spinner" style={{ width: 14, height: 14 }} />
                  Updating Password...
                </>
              ) : (
                "Update Password"
              )}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
