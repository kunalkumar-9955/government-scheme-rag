"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion } from "framer-motion";
import { profileApi } from "@/lib/api/endpoints";
import type { UserProfile } from "@/types";

const INDIAN_STATES = [
  ["AP", "Andhra Pradesh"], ["AR", "Arunachal Pradesh"], ["AS", "Assam"],
  ["BR", "Bihar"], ["CT", "Chhattisgarh"], ["GA", "Goa"], ["GJ", "Gujarat"],
  ["HR", "Haryana"], ["HP", "Himachal Pradesh"], ["JK", "Jammu & Kashmir"],
  ["JH", "Jharkhand"], ["KA", "Karnataka"], ["KL", "Kerala"], ["MP", "Madhya Pradesh"],
  ["MH", "Maharashtra"], ["MN", "Manipur"], ["ML", "Meghalaya"], ["MZ", "Mizoram"],
  ["NL", "Nagaland"], ["OD", "Odisha"], ["PB", "Punjab"], ["RJ", "Rajasthan"],
  ["SK", "Sikkim"], ["TN", "Tamil Nadu"], ["TG", "Telangana"], ["TR", "Tripura"],
  ["UP", "Uttar Pradesh"], ["UK", "Uttarakhand"], ["WB", "West Bengal"],
  ["DL", "Delhi"], ["PY", "Puducherry"], ["AN", "Andaman & Nicobar"],
];

const profileSchema = z.object({
  full_name: z.string().min(2, "Name is required"),
  date_of_birth: z.string().optional(),
  gender: z.enum(["MALE", "FEMALE", "OTHER", ""]).optional(),
  state: z.string().optional(),
  district: z.string().optional(),
  pincode: z.string().optional(),
  social_category: z.enum(["GENERAL", "OBC", "SC", "ST", "EWS", ""]).optional(),
  annual_income: z.preprocess(
    (v) => (v === "" || v === null || v === undefined ? undefined : Number(v)),
    z.number().positive().optional()
  ),
  is_bpl: z.boolean().optional(),
  is_urban: z.preprocess(
    (v) => (v === "true" ? true : v === "false" ? false : undefined),
    z.boolean().optional()
  ),
  occupation: z.string().optional(),
  education_level: z.string().optional(),
  has_disability: z.boolean().optional(),
  family_size: z.preprocess(
    (v) => (v === "" || v === null || v === undefined ? undefined : Number(v)),
    z.number().int().positive().optional()
  ),
});

type ProfileForm = z.infer<typeof profileSchema>;

export default function ProfilePage() {
  const queryClient = useQueryClient();
  const [saveMsg, setSaveMsg] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["myProfile"],
    queryFn: () => profileApi.getMyProfile(),
  });

  const profile: UserProfile | null = data?.data?.data ?? null;

  const { register, handleSubmit, formState: { errors } } = useForm<ProfileForm>({
    resolver: zodResolver(profileSchema) as any,
    values: profile ? {
      full_name: profile.full_name || "",
      date_of_birth: profile.date_of_birth || "",
      gender: (profile.gender as any) || "",
      state: profile.state || "",
      district: profile.district || "",
      pincode: profile.pincode || "",
      social_category: (profile.social_category as any) || "",
      annual_income: profile.annual_income || undefined,
      is_bpl: profile.is_bpl || false,
      is_urban: profile.is_urban ?? undefined,
      occupation: profile.occupation || "",
      education_level: profile.education_level || "",
      has_disability: profile.has_disability || false,
      family_size: profile.family_size || undefined,
    } : undefined,
  });

  const mutation = useMutation({
    mutationFn: (data: ProfileForm) => profileApi.updateMyProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["myProfile"] });
      setSaveMsg("Profile saved successfully!");
      setTimeout(() => setSaveMsg(""), 3000);
    },
  });

  const onSubmit = (data: ProfileForm) => mutation.mutate(data);

  const completionScore = profile?.profile_completion_score ?? 0;

  if (isLoading) {
    return (
      <div style={{ padding: "2rem", display: "flex", alignItems: "center", gap: "1rem" }}>
        <div className="spinner" />
        <span style={{ color: "var(--color-text-muted)" }}>Loading profile...</span>
      </div>
    );
  }

  return (
    <div style={{ padding: "2rem", maxWidth: 760, margin: "0 auto" }}>
      <div style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "1.75rem", marginBottom: "0.5rem" }}>My Profile</h1>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "1rem" }}>
          A complete profile enables accurate eligibility matching across all government schemes.
        </p>

        {/* Completion Bar */}
        <div style={{ background: "var(--color-bg-elevated)", borderRadius: "var(--radius-lg)", padding: "1rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
            <span style={{ fontSize: "0.875rem", fontWeight: 500 }}>Profile Completion</span>
            <span style={{
              fontWeight: 700,
              color: completionScore >= 70 ? "var(--color-success)" : completionScore >= 40 ? "var(--color-warning)" : "var(--color-error)"
            }}>
              {completionScore}%
            </span>
          </div>
          <div className="progress-bar">
            <div
              className="progress-bar-fill"
              style={{
                width: `${completionScore}%`,
                background: completionScore >= 70 ? "var(--gradient-accent)" : "var(--gradient-primary)",
              }}
            />
          </div>
          {completionScore < 70 && (
            <p style={{ fontSize: "0.78rem", color: "var(--color-text-muted)", marginTop: "0.5rem" }}>
              💡 Complete your profile to unlock accurate scheme eligibility matching.
            </p>
          )}
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)}>
        {saveMsg && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            style={{
              padding: "0.75rem 1rem",
              background: "hsla(145, 65%, 45%, 0.12)",
              border: "1px solid hsla(145, 65%, 45%, 0.25)",
              borderRadius: "var(--radius-md)",
              color: "var(--color-success)",
              fontSize: "0.875rem",
              marginBottom: "1.5rem",
            }}
          >
            ✅ {saveMsg}
          </motion.div>
        )}

        {/* Personal Information */}
        <section className="card" style={{ marginBottom: "1.5rem" }}>
          <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1.25rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            👤 Personal Information
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 500, marginBottom: "0.4rem", color: "var(--color-text-secondary)" }}>
                Full Name *
              </label>
              <input {...register("full_name")} className="input-field" placeholder="Enter your full name" />
              {errors.full_name && <p style={{ color: "var(--color-error)", fontSize: "0.75rem", marginTop: "0.25rem" }}>{errors.full_name.message}</p>}
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 500, marginBottom: "0.4rem", color: "var(--color-text-secondary)" }}>
                Date of Birth
              </label>
              <input {...register("date_of_birth")} type="date" className="input-field" />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 500, marginBottom: "0.4rem", color: "var(--color-text-secondary)" }}>
                Gender
              </label>
              <select {...register("gender")} className="input-field">
                <option value="">Select gender</option>
                <option value="MALE">Male</option>
                <option value="FEMALE">Female</option>
                <option value="OTHER">Other</option>
              </select>
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 500, marginBottom: "0.4rem", color: "var(--color-text-secondary)" }}>
                Family Size
              </label>
              <input {...register("family_size")} type="number" min="1" max="20" className="input-field" placeholder="Number of family members" />
            </div>
          </div>
        </section>

        {/* Location */}
        <section className="card" style={{ marginBottom: "1.5rem" }}>
          <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1.25rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            📍 Location
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 500, marginBottom: "0.4rem", color: "var(--color-text-secondary)" }}>State</label>
              <select {...register("state")} className="input-field">
                <option value="">Select state</option>
                {INDIAN_STATES.map(([code, name]) => (
                  <option key={code} value={code}>{name}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 500, marginBottom: "0.4rem", color: "var(--color-text-secondary)" }}>District</label>
              <input {...register("district")} className="input-field" placeholder="District name" />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 500, marginBottom: "0.4rem", color: "var(--color-text-secondary)" }}>PIN Code</label>
              <input {...register("pincode")} className="input-field" placeholder="6-digit PIN code" maxLength={6} />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 500, marginBottom: "0.4rem", color: "var(--color-text-secondary)" }}>Area Type</label>
              <select {...register("is_urban")} className="input-field">
                <option value="">Select area type</option>
                <option value="true">Urban</option>
                <option value="false">Rural</option>
              </select>
            </div>
          </div>
        </section>

        {/* Social & Economic */}
        <section className="card" style={{ marginBottom: "1.5rem" }}>
          <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1.25rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            🏛️ Social & Economic Background
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 500, marginBottom: "0.4rem", color: "var(--color-text-secondary)" }}>Social Category</label>
              <select {...register("social_category")} className="input-field">
                <option value="">Select category</option>
                <option value="GENERAL">General</option>
                <option value="OBC">OBC</option>
                <option value="SC">SC</option>
                <option value="ST">ST</option>
                <option value="EWS">EWS</option>
              </select>
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 500, marginBottom: "0.4rem", color: "var(--color-text-secondary)" }}>Annual Income (₹)</label>
              <input {...register("annual_income")} type="number" min="0" className="input-field" placeholder="Annual household income" />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 500, marginBottom: "0.4rem", color: "var(--color-text-secondary)" }}>Occupation</label>
              <select {...register("occupation")} className="input-field">
                <option value="">Select occupation</option>
                <option value="FARMER">Farmer / Agricultural Worker</option>
                <option value="SELF_EMPLOYED">Self-Employed / Business</option>
                <option value="PRIVATE_EMPLOYEE">Private Sector Employee</option>
                <option value="GOVERNMENT_EMPLOYEE">Government Employee</option>
                <option value="UNEMPLOYED">Unemployed</option>
                <option value="STUDENT">Student</option>
                <option value="HOMEMAKER">Homemaker</option>
                <option value="DAILY_WAGER">Daily Wager</option>
                <option value="RETIRED">Retired</option>
              </select>
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 500, marginBottom: "0.4rem", color: "var(--color-text-secondary)" }}>Education Level</label>
              <select {...register("education_level")} className="input-field">
                <option value="">Select education</option>
                <option value="NO_FORMAL">No Formal Education</option>
                <option value="PRIMARY">Primary (Class 1-5)</option>
                <option value="MIDDLE">Middle (Class 6-8)</option>
                <option value="SECONDARY">Secondary (Class 9-10)</option>
                <option value="HIGHER_SECONDARY">Higher Secondary (11-12)</option>
                <option value="DIPLOMA">Diploma / ITI</option>
                <option value="GRADUATE">Graduate</option>
                <option value="POST_GRADUATE">Post Graduate</option>
              </select>
            </div>
          </div>

          {/* Checkbox fields */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginTop: "1rem" }}>
            {[
              { name: "is_bpl", label: "BPL (Below Poverty Line) cardholder" },
              { name: "has_disability", label: "Person with Disability (PwD)" },
            ].map((field) => (
              <label
                key={field.name}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  padding: "0.6rem 0.75rem",
                  background: "var(--color-bg-overlay)",
                  borderRadius: "var(--radius-md)",
                  cursor: "pointer",
                  fontSize: "0.85rem",
                  color: "var(--color-text-secondary)",
                }}
              >
                <input {...register(field.name as any)} type="checkbox" style={{ width: 16, height: 16, accentColor: "var(--color-primary)" }} />
                {field.label}
              </label>
            ))}
          </div>
        </section>

        <button
          type="submit"
          className="btn-primary"
          disabled={mutation.isPending}
          style={{ fontSize: "0.95rem", padding: "0.8rem 2rem" }}
        >
          {mutation.isPending ? (
            <><div className="spinner" style={{ width: 16, height: 16 }} /> Saving...</>
          ) : (
            "💾 Save Profile"
          )}
        </button>
      </form>
    </div>
  );
}
