"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion } from "framer-motion";
import { authApi } from "@/lib/api/endpoints";

const forgotSchema = z.object({
  email: z.string().email("Invalid email address"),
});

type ForgotForm = z.infer<typeof forgotSchema>;

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [serverMsg, setServerMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotForm>({ resolver: zodResolver(forgotSchema) });

  const onSubmit = async (data: ForgotForm) => {
    setIsLoading(true);
    setServerMsg(null);
    try {
      const res = await authApi.forgotPassword(data.email);
      setServerMsg({
        type: "success",
        text: res.data.message || "If this email is registered, a password reset OTP has been sent.",
      });
      setTimeout(() => {
        router.push(`/reset-password?email=${encodeURIComponent(data.email)}`);
      }, 2000);
    } catch (err: any) {
      setServerMsg({
        type: "error",
        text: err.response?.data?.error?.message || "Failed to send reset code. Please try again.",
      });
    } finally {
      setIsLoading(false);
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
        style={{ width: "100%", maxWidth: "440px", position: "relative" }}
      >
        <div style={{ textAlign: "center", marginBottom: "2rem" }}>
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
          <h1 style={{ fontSize: "1.75rem", marginTop: "1.5rem", marginBottom: "0.5rem" }}>
            Reset Password
          </h1>
          <p style={{ color: "var(--color-text-secondary)", fontSize: "0.9rem" }}>
            Enter your email to receive a 6-digit verification code
          </p>
        </div>

        <div className="card-elevated" style={{ borderRadius: "var(--radius-xl)" }}>
          <form onSubmit={handleSubmit(onSubmit)} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            {serverMsg && (
              <div
                style={{
                  padding: "0.75rem 1rem",
                  borderRadius: "var(--radius-md)",
                  fontSize: "0.875rem",
                  background: serverMsg.type === "success" ? "hsla(145, 65%, 45%, 0.12)" : "hsla(0, 75%, 60%, 0.1)",
                  border: serverMsg.type === "success" ? "1px solid hsla(145, 65%, 45%, 0.25)" : "1px solid hsla(0, 75%, 60%, 0.25)",
                  color: serverMsg.type === "success" ? "var(--color-success)" : "var(--color-error)",
                }}
              >
                {serverMsg.type === "success" ? "✅" : "⚠️"} {serverMsg.text}
              </div>
            )}

            <div>
              <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.5rem" }}>
                Email Address
              </label>
              <input
                {...register("email")}
                type="email"
                className="input-field"
                placeholder="you@example.com"
                autoComplete="email"
              />
              {errors.email && (
                <p style={{ color: "var(--color-error)", fontSize: "0.8rem", marginTop: "0.25rem" }}>
                  {errors.email.message}
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
                  Sending Code...
                </>
              ) : (
                "Send Reset Code →"
              )}
            </button>
          </form>

          <p style={{ textAlign: "center", marginTop: "1.5rem", fontSize: "0.875rem", color: "var(--color-text-secondary)" }}>
            Remembered your password?{" "}
            <Link href="/login" style={{ color: "var(--color-primary-light)", textDecoration: "none", fontWeight: 500 }}>
              Sign In
            </Link>
          </p>
        </div>
      </motion.div>
    </main>
  );
}
