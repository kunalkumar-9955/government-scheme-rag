"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion } from "framer-motion";
import { useAuthStore } from "@/store/authStore";

const loginSchema = z.object({
  email: z.string().email("Invalid email address"),
  password: z.string().min(1, "Password is required"),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const { login, loginDemo, isLoading, error, isAuthenticated, clearError } = useAuthStore();
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });

  const handleInstantDemo = (role: "CITIZEN" | "ADMIN") => {
    loginDemo(role);
    router.push("/dashboard/chat");
  };

  const fillAndSubmit = async (emailVal: string, passVal: string) => {
    setValue("email", emailVal, { shouldValidate: true });
    setValue("password", passVal, { shouldValidate: true });
    try {
      await login(emailVal, passVal);
      router.push("/dashboard/chat");
    } catch {
      // Handled in store
    }
  };

  useEffect(() => {
    if (isAuthenticated) router.replace("/dashboard/chat");
    return () => clearError();
  }, [isAuthenticated]);

  const onSubmit = async (data: LoginForm) => {
    try {
      await login(data.email, data.password);
      router.push("/dashboard/chat");
    } catch {
      // Error displayed from store
    }
  };

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "var(--color-bg-base)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "2rem",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Background gradient */}
      <div
        style={{
          position: "absolute",
          top: "10%",
          left: "50%",
          transform: "translateX(-50%)",
          width: "600px",
          height: "400px",
          background: "radial-gradient(ellipse, hsla(230, 85%, 60%, 0.1) 0%, transparent 70%)",
          pointerEvents: "none",
        }}
      />

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        style={{ width: "100%", maxWidth: "460px", position: "relative" }}
      >
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: "1.5rem" }}>
          <Link href="/" style={{ textDecoration: "none" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "0.75rem" }}>
              <span style={{ fontSize: "2rem" }}>🏛️</span>
              <span
                style={{
                  fontFamily: "Space Grotesk",
                  fontWeight: 700,
                  fontSize: "1.3rem",
                  background: "var(--gradient-primary)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                }}
              >
                GovScheme AI
              </span>
            </div>
          </Link>
          <h1 style={{ fontSize: "1.75rem", marginTop: "1.25rem", marginBottom: "0.4rem" }}>
            Welcome back
          </h1>
          <p style={{ color: "var(--color-text-secondary)", fontSize: "0.9rem" }}>
            Sign in or use a demo account to explore instantly
          </p>
        </div>

        <div className="card-elevated" style={{ borderRadius: "var(--radius-xl)" }}>
          {/* Quick Demo Access Bar */}
          <div
            style={{
              background: "rgba(99, 102, 241, 0.08)",
              border: "1px solid rgba(99, 102, 241, 0.25)",
              borderRadius: "var(--radius-lg)",
              padding: "0.85rem",
              marginBottom: "1.25rem",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.5rem" }}>
              <span style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--color-primary-light)" }}>
                ✨ 1-Click Demo Accounts
              </span>
              <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)" }}>Instant Login</span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
              <button
                type="button"
                onClick={() => handleInstantDemo("CITIZEN")}
                disabled={isLoading}
                style={{
                  padding: "0.5rem 0.6rem",
                  borderRadius: "var(--radius-md)",
                  background: "rgba(255, 255, 255, 0.05)",
                  border: "1px solid rgba(255, 255, 255, 0.12)",
                  color: "var(--color-text-primary)",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  cursor: "pointer",
                  textAlign: "left",
                  transition: "all 0.2s",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
                  <span>👤</span>
                  <span>Citizen Demo</span>
                </div>
                <div style={{ fontSize: "0.7rem", color: "var(--color-text-muted)", marginTop: "2px" }}>
                  Farmer Profile (UP)
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleInstantDemo("ADMIN")}
                disabled={isLoading}
                style={{
                  padding: "0.5rem 0.6rem",
                  borderRadius: "var(--radius-md)",
                  background: "rgba(255, 255, 255, 0.05)",
                  border: "1px solid rgba(255, 255, 255, 0.12)",
                  color: "var(--color-text-primary)",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  cursor: "pointer",
                  textAlign: "left",
                  transition: "all 0.2s",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
                  <span>🛡️</span>
                  <span>Admin Demo</span>
                </div>
                <div style={{ fontSize: "0.7rem", color: "var(--color-text-muted)", marginTop: "2px" }}>
                  Admin Panel & Docs
                </div>
              </button>
            </div>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} style={{ display: "flex", flexDirection: "column", gap: "1.1rem" }}>
            {/* Global error */}
            {error && (
              <div
                className="badge-error"
                style={{
                  padding: "0.75rem 1rem",
                  borderRadius: "var(--radius-md)",
                  fontSize: "0.875rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  background: "hsla(0, 75%, 60%, 0.1)",
                  border: "1px solid hsla(0, 75%, 60%, 0.25)",
                  color: "var(--color-error)",
                }}
              >
                ⚠️ {error}
              </div>
            )}

            {/* Email */}
            <div>
              <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.4rem" }}>
                Email Address
              </label>
              <input
                {...register("email")}
                type="email"
                className="input-field"
                placeholder="you@example.com or demo@govscheme.ai"
                autoComplete="email"
              />
              {errors.email && (
                <p style={{ color: "var(--color-error)", fontSize: "0.8rem", marginTop: "0.25rem" }}>
                  {errors.email.message}
                </p>
              )}
            </div>

            {/* Password */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.4rem" }}>
                <label style={{ fontSize: "0.875rem", fontWeight: 500 }}>Password</label>
                <Link
                  href="/forgot-password"
                  style={{ fontSize: "0.8rem", color: "var(--color-primary-light)", textDecoration: "none" }}
                >
                  Forgot password?
                </Link>
              </div>
              <div style={{ position: "relative" }}>
                <input
                  {...register("password")}
                  type={showPassword ? "text" : "password"}
                  className="input-field"
                  placeholder="••••••••"
                  autoComplete="current-password"
                  style={{ paddingRight: "3rem" }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: "absolute",
                    right: "0.75rem",
                    top: "50%",
                    transform: "translateY(-50%)",
                    background: "none",
                    border: "none",
                    color: "var(--color-text-muted)",
                    cursor: "pointer",
                    fontSize: "1rem",
                  }}
                >
                  {showPassword ? "🙈" : "👁️"}
                </button>
              </div>
              {errors.password && (
                <p style={{ color: "var(--color-error)", fontSize: "0.8rem", marginTop: "0.25rem" }}>
                  {errors.password.message}
                </p>
              )}
            </div>

            <button
              type="submit"
              className="btn-primary"
              disabled={isLoading}
              style={{ width: "100%", justifyContent: "center", padding: "0.8rem", fontSize: "0.95rem" }}
            >
              {isLoading ? (
                <>
                  <div className="spinner" style={{ width: 16, height: 16 }} />
                  Signing in...
                </>
              ) : (
                "Sign In →"
              )}
            </button>
          </form>

          <p style={{ textAlign: "center", marginTop: "1.25rem", fontSize: "0.875rem", color: "var(--color-text-secondary)" }}>
            Don't have an account?{" "}
            <Link href="/register" style={{ color: "var(--color-primary-light)", textDecoration: "none", fontWeight: 500 }}>
              Create one free
            </Link>
          </p>
        </div>
      </motion.div>
    </main>
  );
}
