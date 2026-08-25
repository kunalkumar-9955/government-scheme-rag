"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, Suspense } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion } from "framer-motion";
import { authApi } from "@/lib/api/endpoints";

const resetSchema = z
  .object({
    email: z.string().email("Invalid email address"),
    otp_code: z.string().length(6, "Code must be exactly 6 digits"),
    new_password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .regex(/[A-Z]/, "Must contain an uppercase letter")
      .regex(/[0-9]/, "Must contain a number"),
    new_password_confirm: z.string().min(1, "Please confirm your password"),
  })
  .refine((d) => d.new_password === d.new_password_confirm, {
    message: "Passwords do not match",
    path: ["new_password_confirm"],
  });

type ResetForm = z.infer<typeof resetSchema>;

function ResetPasswordContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const emailParam = searchParams.get("email") || "";

  const [isLoading, setIsLoading] = useState(false);
  const [serverMsg, setServerMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetForm>({
    resolver: zodResolver(resetSchema),
    defaultValues: {
      email: emailParam,
    },
  });

  const onSubmit = async (data: ResetForm) => {
    setIsLoading(true);
    setServerMsg(null);
    try {
      const res = await authApi.resetPassword(data);
      setServerMsg({
        type: "success",
        text: res.data.message || "Password has been reset successfully! Redirecting to login...",
      });
      setTimeout(() => {
        router.push("/login");
      }, 2000);
    } catch (err: any) {
      setServerMsg({
        type: "error",
        text: err.response?.data?.error?.message || "Password reset failed. Check your OTP code.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      style={{ width: "100%", maxWidth: "460px", position: "relative" }}
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
          Enter Reset Code
        </h1>
        <p style={{ color: "var(--color-text-secondary)", fontSize: "0.9rem" }}>
          Provide the 6-digit OTP sent to your email and your new password
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
            />
            {errors.email && (
              <p style={{ color: "var(--color-error)", fontSize: "0.8rem", marginTop: "0.25rem" }}>
                {errors.email.message}
              </p>
            )}
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.5rem" }}>
              6-Digit OTP Code
            </label>
            <input
              {...register("otp_code")}
              type="text"
              maxLength={6}
              className="input-field"
              placeholder="123456"
              style={{ letterSpacing: "0.2em", fontSize: "1.1rem", textAlign: "center" }}
            />
            {errors.otp_code && (
              <p style={{ color: "var(--color-error)", fontSize: "0.8rem", marginTop: "0.25rem" }}>
                {errors.otp_code.message}
              </p>
            )}
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.5rem" }}>
              New Password
            </label>
            <input
              {...register("new_password")}
              type="password"
              className="input-field"
              placeholder="Min 8 chars, uppercase, number"
            />
            {errors.new_password && (
              <p style={{ color: "var(--color-error)", fontSize: "0.8rem", marginTop: "0.25rem" }}>
                {errors.new_password.message}
              </p>
            )}
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.5rem" }}>
              Confirm New Password
            </label>
            <input
              {...register("new_password_confirm")}
              type="password"
              className="input-field"
              placeholder="Repeat new password"
            />
            {errors.new_password_confirm && (
              <p style={{ color: "var(--color-error)", fontSize: "0.8rem", marginTop: "0.25rem" }}>
                {errors.new_password_confirm.message}
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
                Resetting Password...
              </>
            ) : (
              "Save New Password →"
            )}
          </button>
        </form>

        <p style={{ textAlign: "center", marginTop: "1.5rem", fontSize: "0.875rem", color: "var(--color-text-secondary)" }}>
          Back to{" "}
          <Link href="/login" style={{ color: "var(--color-primary-light)", textDecoration: "none", fontWeight: 500 }}>
            Sign In
          </Link>
        </p>
      </div>
    </motion.div>
  );
}

export default function ResetPasswordPage() {
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
      <Suspense fallback={<div className="spinner" />}>
        <ResetPasswordContent />
      </Suspense>
    </main>
  );
}
