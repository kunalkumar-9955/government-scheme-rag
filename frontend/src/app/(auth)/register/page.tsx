"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion } from "framer-motion";
import { useAuthStore } from "@/store/authStore";

const registerSchema = z
  .object({
    email: z.string().email("Invalid email address"),
    password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .regex(/[A-Z]/, "Must contain an uppercase letter")
      .regex(/[0-9]/, "Must contain a number"),
    password_confirm: z.string().min(1, "Please confirm your password"),
  })
  .refine((d) => d.password === d.password_confirm, {
    message: "Passwords do not match",
    path: ["password_confirm"],
  });

type RegisterForm = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const { register: registerUser, isLoading, error, isAuthenticated, clearError } = useAuthStore();

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<RegisterForm>({ resolver: zodResolver(registerSchema) });

  const password = watch("password", "");

  useEffect(() => {
    if (isAuthenticated) router.replace("/dashboard/chat");
    return () => clearError();
  }, [isAuthenticated]);

  const onSubmit = async (data: RegisterForm) => {
    try {
      await registerUser(data.email, data.password, data.password_confirm);
      router.push("/dashboard/profile");
    } catch {
      // Error from store
    }
  };

  const passwordStrength = (() => {
    let score = 0;
    if (password.length >= 8) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;
    return score;
  })();

  const strengthColors = ["", "var(--color-error)", "var(--color-warning)", "var(--color-warning)", "var(--color-success)"];
  const strengthLabels = ["", "Weak", "Fair", "Good", "Strong"];

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
          top: "5%",
          right: "10%",
          width: "500px",
          height: "400px",
          background: "radial-gradient(ellipse, hsla(160, 80%, 45%, 0.07) 0%, transparent 70%)",
          pointerEvents: "none",
        }}
      />

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        style={{ width: "100%", maxWidth: "480px", position: "relative" }}
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
            Create Your Account
          </h1>
          <p style={{ color: "var(--color-text-secondary)", fontSize: "0.9rem" }}>
            Free forever. Discover schemes you qualify for.
          </p>
        </div>

        <div className="card-elevated" style={{ borderRadius: "var(--radius-xl)" }}>
          <form onSubmit={handleSubmit(onSubmit)} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            {error && (
              <div
                style={{
                  padding: "0.75rem 1rem",
                  borderRadius: "var(--radius-md)",
                  fontSize: "0.875rem",
                  background: "hsla(0, 75%, 60%, 0.1)",
                  border: "1px solid hsla(0, 75%, 60%, 0.25)",
                  color: "var(--color-error)",
                }}
              >
                ⚠️ {error}
              </div>
            )}

            <div>
              <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.5rem" }}>
                Email Address
              </label>
              <input {...register("email")} type="email" className="input-field" placeholder="you@example.com" />
              {errors.email && (
                <p style={{ color: "var(--color-error)", fontSize: "0.8rem", marginTop: "0.25rem" }}>{errors.email.message}</p>
              )}
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.5rem" }}>
                Password
              </label>
              <input {...register("password")} type="password" className="input-field" placeholder="Min 8 chars, uppercase, number" />
              {/* Password strength meter */}
              {password && (
                <div style={{ marginTop: "0.5rem" }}>
                  <div className="progress-bar">
                    <div
                      className="progress-bar-fill"
                      style={{
                        width: `${(passwordStrength / 4) * 100}%`,
                        background: strengthColors[passwordStrength],
                      }}
                    />
                  </div>
                  <span style={{ fontSize: "0.75rem", color: strengthColors[passwordStrength], marginTop: "0.25rem", display: "block" }}>
                    {strengthLabels[passwordStrength]}
                  </span>
                </div>
              )}
              {errors.password && (
                <p style={{ color: "var(--color-error)", fontSize: "0.8rem", marginTop: "0.25rem" }}>{errors.password.message}</p>
              )}
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.5rem" }}>
                Confirm Password
              </label>
              <input {...register("password_confirm")} type="password" className="input-field" placeholder="Repeat your password" />
              {errors.password_confirm && (
                <p style={{ color: "var(--color-error)", fontSize: "0.8rem", marginTop: "0.25rem" }}>{errors.password_confirm.message}</p>
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
                  Creating account...
                </>
              ) : (
                "Create Free Account →"
              )}
            </button>

            <p style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", textAlign: "center" }}>
              By registering, you agree to our Terms of Service. Your data is used only for scheme matching.
            </p>
          </form>

          <p style={{ textAlign: "center", marginTop: "1.5rem", fontSize: "0.875rem", color: "var(--color-text-secondary)" }}>
            Already have an account?{" "}
            <Link href="/login" style={{ color: "var(--color-primary-light)", textDecoration: "none", fontWeight: 500 }}>
              Sign in
            </Link>
          </p>
        </div>
      </motion.div>
    </main>
  );
}
