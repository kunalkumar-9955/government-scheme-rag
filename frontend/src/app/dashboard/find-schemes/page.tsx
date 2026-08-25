"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { userApi, schemesApi, eligibilityApi } from "@/lib/api/endpoints";

const INDIAN_STATES = [
  { code: "AN", name: "Andaman and Nicobar Islands" },
  { code: "AP", name: "Andhra Pradesh" },
  { code: "AR", name: "Arunachal Pradesh" },
  { code: "AS", name: "Assam" },
  { code: "BR", name: "Bihar" },
  { code: "CH", name: "Chandigarh" },
  { code: "CG", name: "Chhattisgarh" },
  { code: "DH", name: "Dadra and Nagar Haveli and Daman and Diu" },
  { code: "DL", name: "Delhi" },
  { code: "GA", name: "Goa" },
  { code: "GJ", name: "Gujarat" },
  { code: "HR", name: "Haryana" },
  { code: "HP", name: "Himachal Pradesh" },
  { code: "JK", name: "Jammu and Kashmir" },
  { code: "JH", name: "Jharkhand" },
  { code: "KA", name: "Karnataka" },
  { code: "KL", name: "Kerala" },
  { code: "LA", name: "Ladakh" },
  { code: "LD", name: "Lakshadweep" },
  { code: "MP", name: "Madhya Pradesh" },
  { code: "MH", name: "Maharashtra" },
  { code: "MN", name: "Manipur" },
  { code: "ML", name: "Meghalaya" },
  { code: "MZ", name: "Mizoram" },
  { code: "NL", name: "Nagaland" },
  { code: "OR", name: "Odisha" },
  { code: "PY", name: "Puducherry" },
  { code: "PB", name: "Punjab" },
  { code: "RJ", name: "Rajasthan" },
  { code: "SK", name: "Sikkim" },
  { code: "TN", name: "Tamil Nadu" },
  { code: "TG", name: "Telangana" },
  { code: "TR", name: "Tripura" },
  { code: "UP", name: "Uttar Pradesh" },
  { code: "UT", name: "Uttarakhand" },
  { code: "WB", name: "West Bengal" },
];

const OCCUPATIONS = [
  { value: "FARMER", label: "Farmer / Agriculturalist" },
  { value: "STUDENT", label: "Student" },
  { value: "SELF_EMPLOYED", label: "Self Employed / Artisan" },
  { value: "SALARIED", label: "Salaried Private" },
  { value: "GOVERNMENT_EMPLOYEE", label: "Government Employee" },
  { value: "DAILY_WAGE_LABOR", label: "Daily Wage Laborer / Construction Worker" },
  { value: "UNEMPLOYED", label: "Unemployed / Job Seeker" },
  { value: "BUSINESS_OWNER", label: "Small Business / MSME Owner" },
  { value: "HOMEMAKER", label: "Homemaker" },
  { value: "RETIRED", label: "Retired / Senior Citizen" },
];

const EDUCATION_LEVELS = [
  { value: "ILLITERATE", label: "No Formal Education" },
  { value: "PRIMARY", label: "Primary (Class 1-5)" },
  { value: "MIDDLE", label: "Middle (Class 6-8)" },
  { value: "SECONDARY", label: "Secondary / 10th Pass" },
  { value: "HIGHER_SECONDARY", label: "Higher Secondary / 12th Pass" },
  { value: "DIPLOMA", label: "Diploma / Polytechnic" },
  { value: "GRADUATE", label: "Graduate / Bachelor's Degree" },
  { value: "POST_GRADUATE", label: "Post Graduate / Master's" },
  { value: "DOCTORATE", label: "Doctorate / Ph.D" },
];

type ResultCategory = "LIKELY_ELIGIBLE" | "POSSIBLY_ELIGIBLE" | "INSUFFICIENT_INFORMATION" | "NOT_ELIGIBLE" | "ALL";

export default function FindSchemesPage() {
  const [formData, setFormData] = useState({
    age: "",
    state: "",
    district: "",
    occupation: "",
    education_level: "",
    annual_income: "",
    gender: "",
    social_category: "",
    is_bpl: false,
    has_ration_card: false,
    ration_card_type: "",
    is_student: false,
    has_disability: false,
    disability_percentage: "",
    land_holding_acres: "",
    is_minority: false,
    is_widow: false,
    is_ex_serviceman: false,
    is_single_girl_child: false,
  });

  const [activeTab, setActiveTab] = useState<ResultCategory>("ALL");
  const [expandedSchemeId, setExpandedSchemeId] = useState<string | null>(null);
  const [evaluatedResults, setEvaluatedResults] = useState<any[] | null>(null);
  const [searchTerm, setSearchTerm] = useState("");

  // Load user profile to allow pre-filling
  const { data: profileRes, isLoading: isLoadingProfile } = useQuery({
    queryKey: ["userProfile"],
    queryFn: () => userApi.getMyProfile(),
    staleTime: 5 * 60 * 1000,
  });

  const savedProfile = profileRes?.data?.data;

  const handlePreFill = () => {
    if (!savedProfile) return;
    setFormData({
      age: savedProfile.age != null ? String(savedProfile.age) : "",
      state: savedProfile.state || "",
      district: savedProfile.district || "",
      occupation: savedProfile.occupation || "",
      education_level: savedProfile.education_level || "",
      annual_income: savedProfile.annual_income != null ? String(savedProfile.annual_income) : "",
      gender: savedProfile.gender || "",
      social_category: savedProfile.social_category || "",
      is_bpl: Boolean(savedProfile.is_bpl),
      has_ration_card: Boolean(savedProfile.has_ration_card),
      ration_card_type: savedProfile.ration_card_type || "",
      is_student: Boolean(savedProfile.is_student),
      has_disability: Boolean(savedProfile.has_disability),
      disability_percentage: savedProfile.disability_percentage != null ? String(savedProfile.disability_percentage) : "",
      land_holding_acres: savedProfile.land_holding_acres != null ? String(savedProfile.land_holding_acres) : "",
      is_minority: Boolean(savedProfile.is_minority),
      is_widow: Boolean(savedProfile.is_widow),
      is_ex_serviceman: Boolean(savedProfile.is_ex_serviceman),
      is_single_girl_child: Boolean(savedProfile.is_single_girl_child),
    });
  };

  const evaluateMutation = useMutation({
    mutationFn: async () => {
      // Build normalized payload
      const payload: Record<string, any> = {};
      if (formData.age) payload.age = Number(formData.age);
      if (formData.state) payload.state = formData.state;
      if (formData.district) payload.district = formData.district;
      if (formData.occupation) payload.occupation = formData.occupation;
      if (formData.education_level) payload.education_level = formData.education_level;
      if (formData.annual_income) payload.annual_income = Number(formData.annual_income);
      if (formData.gender) payload.gender = formData.gender;
      if (formData.social_category) payload.social_category = formData.social_category;
      payload.is_bpl = formData.is_bpl;
      payload.has_ration_card = formData.has_ration_card;
      if (formData.ration_card_type) payload.ration_card_type = formData.ration_card_type;
      payload.is_student = formData.is_student;
      payload.has_disability = formData.has_disability;
      if (formData.has_disability && formData.disability_percentage) {
        payload.disability_percentage = Number(formData.disability_percentage);
      }
      if (formData.land_holding_acres) {
        payload.land_holding_acres = Number(formData.land_holding_acres);
      }
      payload.is_minority = formData.is_minority;
      payload.is_widow = formData.is_widow;
      payload.is_ex_serviceman = formData.is_ex_serviceman;
      payload.is_single_girl_child = formData.is_single_girl_child;

      const res = await eligibilityApi.evaluateArbitraryProfile({ profile: payload });
      return res.data?.data?.results || [];
    },
    onSuccess: (results) => {
      setEvaluatedResults(results);
      if (results.length > 0) {
        // Default to Likely Eligible tab if any exist
        const hasLikely = results.some((r: any) => r.verdict === "Likely Eligible" || r.verdict === "Eligible");
        setActiveTab(hasLikely ? "LIKELY_ELIGIBLE" : "ALL");
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    evaluateMutation.mutate();
  };

  // Group results
  const likelyEligible = evaluatedResults?.filter((r) => r.verdict === "Likely Eligible" || r.verdict === "Eligible") || [];
  const possiblyEligible = evaluatedResults?.filter((r) => r.verdict === "Possibly Eligible") || [];
  const insufficientInfo = evaluatedResults?.filter((r) => r.verdict === "Insufficient Information") || [];
  const notEligible = evaluatedResults?.filter((r) => r.verdict === "Not Eligible") || [];

  const getFilteredResults = () => {
    if (!evaluatedResults) return [];
    let list = evaluatedResults;
    if (activeTab === "LIKELY_ELIGIBLE") list = likelyEligible;
    else if (activeTab === "POSSIBLY_ELIGIBLE") list = possiblyEligible;
    else if (activeTab === "INSUFFICIENT_INFORMATION") list = insufficientInfo;
    else if (activeTab === "NOT_ELIGIBLE") list = notEligible;

    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      list = list.filter((r) =>
        r.scheme_name.toLowerCase().includes(q) ||
        (r.short_title && r.short_title.toLowerCase().includes(q))
      );
    }
    return list;
  };

  const currentDisplayList = getFilteredResults();

  return (
    <div style={{ padding: "2rem", height: "100%", overflowY: "auto" }}>
      {/* Header */}
      <div style={{ marginBottom: "2rem", display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "0.4rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            🎯 Find Schemes For Me
          </h1>
          <p style={{ color: "var(--color-text-secondary)", fontSize: "0.9rem" }}>
            Provide your demographics and qualification attributes to evaluate deterministic eligibility across all active government schemes.
          </p>
        </div>
        {savedProfile && (
          <button
            onClick={handlePreFill}
            className="btn-secondary"
            style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.85rem" }}
          >
            📋 Auto-Fill From My Profile
          </button>
        )}
      </div>

      {/* Main Grid: Form Left, Results Right */}
      <div style={{ display: "grid", gridTemplateColumns: evaluatedResults ? "360px 1fr" : "minmax(300px, 720px)", gap: "1.5rem", margin: "0 auto", alignItems: "start" }}>
        {/* Profile Attributes Card */}
        <div className="card-elevated" style={{ borderRadius: "var(--radius-xl)", padding: "1.5rem", border: "1px solid var(--color-border)" }}>
          <h3 style={{ fontSize: "1.05rem", fontWeight: 600, marginBottom: "1.2rem", color: "var(--color-text-primary)" }}>
            Citizen Profile Criteria
          </h3>

          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {/* Age & Gender */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 500, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                  Age (Years) *
                </label>
                <input
                  type="number"
                  min="0"
                  max="120"
                  placeholder="e.g. 24"
                  value={formData.age}
                  onChange={(e) => setFormData({ ...formData, age: e.target.value })}
                  className="input-field"
                  required
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 500, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                  Gender
                </label>
                <select
                  value={formData.gender}
                  onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                  className="input-field"
                >
                  <option value="">Select Gender</option>
                  <option value="MALE">Male</option>
                  <option value="FEMALE">Female</option>
                  <option value="OTHER">Other / Transgender</option>
                </select>
              </div>
            </div>

            {/* State & District */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 500, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                  State / UT *
                </label>
                <select
                  value={formData.state}
                  onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                  className="input-field"
                  required
                >
                  <option value="">Select State</option>
                  {INDIAN_STATES.map((s) => (
                    <option key={s.code} value={s.name}>
                      {s.name} ({s.code})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 500, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                  District
                </label>
                <input
                  type="text"
                  placeholder="e.g. Patna, Pune"
                  value={formData.district}
                  onChange={(e) => setFormData({ ...formData, district: e.target.value })}
                  className="input-field"
                />
              </div>
            </div>

            {/* Occupation & Education */}
            <div>
              <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 500, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                Occupation *
              </label>
              <select
                value={formData.occupation}
                onChange={(e) => setFormData({ ...formData, occupation: e.target.value })}
                className="input-field"
                required
              >
                <option value="">Select Occupation</option>
                {OCCUPATIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 500, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                Education Level
              </label>
              <select
                value={formData.education_level}
                onChange={(e) => setFormData({ ...formData, education_level: e.target.value })}
                className="input-field"
              >
                <option value="">Select Education</option>
                {EDUCATION_LEVELS.map((ed) => (
                  <option key={ed.value} value={ed.value}>
                    {ed.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Annual Income & Social Category */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 500, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                  Annual Family Income (₹)
                </label>
                <input
                  type="number"
                  placeholder="e.g. 180000"
                  value={formData.annual_income}
                  onChange={(e) => setFormData({ ...formData, annual_income: e.target.value })}
                  className="input-field"
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 500, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                  Social Category
                </label>
                <select
                  value={formData.social_category}
                  onChange={(e) => setFormData({ ...formData, social_category: e.target.value })}
                  className="input-field"
                >
                  <option value="">General / Open</option>
                  <option value="OBC">OBC (Other Backward Class)</option>
                  <option value="SC">SC (Scheduled Caste)</option>
                  <option value="ST">ST (Scheduled Tribe)</option>
                  <option value="EWS">EWS (Economically Weaker Section)</option>
                </select>
              </div>
            </div>

            {/* Additional Attributes Checkboxes */}
            <div style={{ borderTop: "1px solid var(--color-border)", paddingTop: "0.8rem" }}>
              <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--color-text-muted)", marginBottom: "0.5rem", textTransform: "uppercase" }}>
                Specific Qualifications
              </p>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
                <label style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.8rem", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={formData.is_bpl}
                    onChange={(e) => setFormData({ ...formData, is_bpl: e.target.checked })}
                  />
                  BPL Family
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.8rem", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={formData.is_student}
                    onChange={(e) => setFormData({ ...formData, is_student: e.target.checked })}
                  />
                  Current Student
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.8rem", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={formData.has_disability}
                    onChange={(e) => setFormData({ ...formData, has_disability: e.target.checked })}
                  />
                  Person w/ Disability
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.8rem", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={formData.is_minority}
                    onChange={(e) => setFormData({ ...formData, is_minority: e.target.checked })}
                  />
                  Minority Community
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.8rem", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={formData.is_widow}
                    onChange={(e) => setFormData({ ...formData, is_widow: e.target.checked })}
                  />
                  Widow
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.8rem", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={formData.is_single_girl_child}
                    onChange={(e) => setFormData({ ...formData, is_single_girl_child: e.target.checked })}
                  />
                  Single Girl Child
                </label>
              </div>
            </div>

            {/* Land Holding (If Farmer) */}
            {formData.occupation === "FARMER" && (
              <div>
                <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 500, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                  Agricultural Land Holding (Acres)
                </label>
                <input
                  type="number"
                  step="0.1"
                  placeholder="e.g. 2.5"
                  value={formData.land_holding_acres}
                  onChange={(e) => setFormData({ ...formData, land_holding_acres: e.target.value })}
                  className="input-field"
                />
              </div>
            )}

            <button
              type="submit"
              disabled={evaluateMutation.isPending}
              className="btn-primary"
              style={{ marginTop: "0.5rem", padding: "0.75rem", fontSize: "0.95rem", fontWeight: 600, display: "flex", alignItems: "center", justifyContent: "center", gap: "0.5rem" }}
            >
              {evaluateMutation.isPending ? (
                <>
                  <div className="spinner" style={{ width: 16, height: 16 }} />
                  Evaluating Schemes...
                </>
              ) : (
                "🔍 Evaluate My Eligibility"
              )}
            </button>
          </form>
        </div>

        {/* Results Panel */}
        {evaluatedResults && (
          <div>
            {/* Verdict Summary Tabs */}
            <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.2rem", flexWrap: "wrap" }}>
              <button
                onClick={() => setActiveTab("ALL")}
                className={`card ${activeTab === "ALL" ? "border-primary" : ""}`}
                style={{
                  padding: "0.5rem 0.9rem",
                  cursor: "pointer",
                  fontSize: "0.82rem",
                  fontWeight: 600,
                  background: activeTab === "ALL" ? "var(--color-bg-elevated)" : "var(--color-bg-surface)",
                  border: activeTab === "ALL" ? "1px solid var(--color-primary)" : "1px solid var(--color-border)",
                  borderRadius: "var(--radius-md)",
                }}
              >
                All Schemes ({evaluatedResults.length})
              </button>
              <button
                onClick={() => setActiveTab("LIKELY_ELIGIBLE")}
                className={`card ${activeTab === "LIKELY_ELIGIBLE" ? "border-success" : ""}`}
                style={{
                  padding: "0.5rem 0.9rem",
                  cursor: "pointer",
                  fontSize: "0.82rem",
                  fontWeight: 600,
                  background: activeTab === "LIKELY_ELIGIBLE" ? "var(--color-bg-elevated)" : "var(--color-bg-surface)",
                  border: activeTab === "LIKELY_ELIGIBLE" ? "1px solid var(--color-success)" : "1px solid var(--color-border)",
                  borderRadius: "var(--radius-md)",
                  color: "var(--color-success)",
                }}
              >
                ✅ Likely Eligible ({likelyEligible.length})
              </button>
              <button
                onClick={() => setActiveTab("POSSIBLY_ELIGIBLE")}
                className={`card ${activeTab === "POSSIBLY_ELIGIBLE" ? "border-accent" : ""}`}
                style={{
                  padding: "0.5rem 0.9rem",
                  cursor: "pointer",
                  fontSize: "0.82rem",
                  fontWeight: 600,
                  background: activeTab === "POSSIBLY_ELIGIBLE" ? "var(--color-bg-elevated)" : "var(--color-bg-surface)",
                  border: activeTab === "POSSIBLY_ELIGIBLE" ? "1px solid var(--color-accent)" : "1px solid var(--color-border)",
                  borderRadius: "var(--radius-md)",
                  color: "var(--color-accent)",
                }}
              >
                ⚡ Possibly Eligible ({possiblyEligible.length})
              </button>
              <button
                onClick={() => setActiveTab("INSUFFICIENT_INFORMATION")}
                className={`card ${activeTab === "INSUFFICIENT_INFORMATION" ? "border-info" : ""}`}
                style={{
                  padding: "0.5rem 0.9rem",
                  cursor: "pointer",
                  fontSize: "0.82rem",
                  fontWeight: 600,
                  background: activeTab === "INSUFFICIENT_INFORMATION" ? "var(--color-bg-elevated)" : "var(--color-bg-surface)",
                  border: activeTab === "INSUFFICIENT_INFORMATION" ? "1px solid var(--color-primary)" : "1px solid var(--color-border)",
                  borderRadius: "var(--radius-md)",
                  color: "var(--color-primary)",
                }}
              >
                ❓ Insufficient Info ({insufficientInfo.length})
              </button>
              <button
                onClick={() => setActiveTab("NOT_ELIGIBLE")}
                className={`card ${activeTab === "NOT_ELIGIBLE" ? "border-danger" : ""}`}
                style={{
                  padding: "0.5rem 0.9rem",
                  cursor: "pointer",
                  fontSize: "0.82rem",
                  fontWeight: 600,
                  background: activeTab === "NOT_ELIGIBLE" ? "var(--color-bg-elevated)" : "var(--color-bg-surface)",
                  border: activeTab === "NOT_ELIGIBLE" ? "1px solid var(--color-danger)" : "1px solid var(--color-border)",
                  borderRadius: "var(--radius-md)",
                  color: "var(--color-text-muted)",
                }}
              >
                ❌ Not Eligible ({notEligible.length})
              </button>
            </div>

            {/* Search Filter */}
            <div style={{ marginBottom: "1rem" }}>
              <input
                type="text"
                placeholder="Filter results by scheme name..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="input-field"
                style={{ width: "100%", maxWidth: "400px" }}
              />
            </div>

            {/* Scheme Cards List */}
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              {currentDisplayList.length === 0 ? (
                <div className="card" style={{ padding: "2rem", textAlign: "center", color: "var(--color-text-muted)" }}>
                  No schemes found in this category.
                </div>
              ) : (
                currentDisplayList.map((scheme) => {
                  const isExpanded = expandedSchemeId === scheme.scheme_id;
                  const isLikely = scheme.verdict === "Likely Eligible" || scheme.verdict === "Eligible";
                  const isPossible = scheme.verdict === "Possibly Eligible";
                  const isInsufficient = scheme.verdict === "Insufficient Information";

                  return (
                    <motion.div
                      key={scheme.scheme_id}
                      layout
                      className="card-elevated"
                      style={{
                        borderRadius: "var(--radius-lg)",
                        padding: "1.25rem",
                        border: "1px solid var(--color-border)",
                        borderLeft: isLikely
                          ? "4px solid var(--color-success)"
                          : isPossible
                          ? "4px solid var(--color-accent)"
                          : isInsufficient
                          ? "4px solid var(--color-primary)"
                          : "4px solid var(--color-danger)",
                      }}
                    >
                      {/* Top Header */}
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem" }}>
                        <div>
                          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.35rem", flexWrap: "wrap" }}>
                            <span
                              className={`badge ${
                                isLikely
                                  ? "badge-success"
                                  : isPossible
                                  ? "badge-accent"
                                  : isInsufficient
                                  ? "badge-primary"
                                  : "badge-danger"
                              }`}
                            >
                              {scheme.verdict}
                            </span>
                            {scheme.passed_rules?.length > 0 && (
                              <span style={{ fontSize: "0.75rem", color: "var(--color-text-secondary)" }}>
                                {scheme.passed_rules.length} Criteria Passed
                              </span>
                            )}
                          </div>
                          <h3 style={{ fontSize: "1.05rem", fontWeight: 700, margin: 0, color: "var(--color-text-primary)" }}>
                            {scheme.scheme_name}
                          </h3>
                        </div>

                        <div style={{ display: "flex", gap: "0.5rem" }}>
                          <Link
                            href={`/dashboard/chat?query=Tell me about ${encodeURIComponent(scheme.scheme_name)}`}
                            className="btn-ghost"
                            style={{ fontSize: "0.75rem", padding: "0.35rem 0.65rem", textDecoration: "none" }}
                          >
                            💬 Ask AI
                          </Link>
                          <button
                            onClick={() => setExpandedSchemeId(isExpanded ? null : scheme.scheme_id)}
                            className="btn-secondary"
                            style={{ fontSize: "0.75rem", padding: "0.35rem 0.65rem" }}
                          >
                            {isExpanded ? "Hide Details ▲" : "View Rules ▼"}
                          </button>
                        </div>
                      </div>

                      {/* Explanation */}
                      <p style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", marginTop: "0.75rem", lineHeight: 1.6 }}>
                        {scheme.summary_explanation}
                      </p>

                      {/* Expanded Criteria Breakdown */}
                      <AnimatePresence>
                        {isExpanded && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: "auto" }}
                            exit={{ opacity: 0, height: 0 }}
                            style={{ marginTop: "1rem", borderTop: "1px solid var(--color-border)", paddingTop: "1rem" }}
                          >
                            {/* Passed Rules */}
                            {scheme.passed_rules?.length > 0 && (
                              <div style={{ marginBottom: "0.85rem" }}>
                                <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--color-success)", textTransform: "uppercase", marginBottom: "0.35rem" }}>
                                  ✅ Passed Criteria ({scheme.passed_rules.length})
                                </p>
                                <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
                                  {scheme.passed_rules.map((r: any, idx: number) => (
                                    <div
                                      key={idx}
                                      style={{
                                        fontSize: "0.8rem",
                                        padding: "0.4rem 0.6rem",
                                        background: "hsla(150, 70%, 50%, 0.08)",
                                        borderRadius: "var(--radius-sm)",
                                        borderLeft: "2px solid var(--color-success)",
                                      }}
                                    >
                                      <strong>{r.criterion_key}</strong>: {r.rule_description} (Your profile: <em>{String(r.user_value)}</em>)
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Failed Rules */}
                            {scheme.failed_rules?.length > 0 && (
                              <div style={{ marginBottom: "0.85rem" }}>
                                <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--color-danger)", textTransform: "uppercase", marginBottom: "0.35rem" }}>
                                  ❌ Failed Criteria ({scheme.failed_rules.length})
                                </p>
                                <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
                                  {scheme.failed_rules.map((r: any, idx: number) => (
                                    <div
                                      key={idx}
                                      style={{
                                        fontSize: "0.8rem",
                                        padding: "0.4rem 0.6rem",
                                        background: "hsla(0, 80%, 60%, 0.08)",
                                        borderRadius: "var(--radius-sm)",
                                        borderLeft: "2px solid var(--color-danger)",
                                      }}
                                    >
                                      <strong>{r.criterion_key}</strong>: {r.rule_description} — Reason: {r.reason || "Criteria not satisfied"}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Missing Information */}
                            {scheme.missing_information?.length > 0 && (
                              <div style={{ marginBottom: "0.85rem" }}>
                                <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--color-primary)", textTransform: "uppercase", marginBottom: "0.35rem" }}>
                                  ❓ Missing Profile Information
                                </p>
                                <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", background: "var(--color-bg-overlay)", padding: "0.5rem 0.75rem", borderRadius: "var(--radius-sm)" }}>
                                  The following attributes are required to confirm eligibility:{" "}
                                  <strong>{scheme.missing_information.join(", ")}</strong>
                                </div>
                              </div>
                            )}

                            {/* Official Sources */}
                            {scheme.evidence_sources?.length > 0 && (
                              <div style={{ marginTop: "0.75rem" }}>
                                <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--color-text-muted)", textTransform: "uppercase", marginBottom: "0.35rem" }}>
                                  🏛️ Official Sources & Evidence
                                </p>
                                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                                  {scheme.evidence_sources.map((s: any, idx: number) => (
                                    <a
                                      key={idx}
                                      href={s.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="badge badge-primary"
                                      style={{ textDecoration: "none", fontSize: "0.75rem" }}
                                    >
                                      {s.title || "Official Portal"} ↗
                                    </a>
                                  ))}
                                </div>
                              </div>
                            )}
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </motion.div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
