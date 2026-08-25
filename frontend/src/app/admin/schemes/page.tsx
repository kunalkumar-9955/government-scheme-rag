"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { schemesApi } from "@/lib/api/endpoints";

export default function AdminSchemesPage() {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedScheme, setSelectedScheme] = useState<any | null>(null);
  const [isRuleModalOpen, setIsRuleModalOpen] = useState(false);

  // Form State for Scheme Creation / Editing
  const [formData, setFormData] = useState({
    name: "",
    short_title: "",
    category: "",
    ministry: "",
    scheme_type: "CENTRAL_SECTOR",
    description: "",
    version: "1.0",
    official_source_url: "",
    official_application_url: "",
    status: "ACTIVE",
  });

  // Form State for Eligibility Rule Creation
  const [ruleFormData, setRuleFormData] = useState({
    criterion_key: "age",
    operator: "LTE",
    value: "25",
    data_type: "INTEGER",
    is_mandatory: true,
    rule_group: 1,
    rule_description: "",
  });

  // Fetch Categories & Ministries for dropdowns
  const { data: catRes } = useQuery({
    queryKey: ["schemeCategories"],
    queryFn: () => schemesApi.getCategories(),
  });

  const { data: ministryRes } = useQuery({
    queryKey: ["schemeMinistries"],
    queryFn: () => schemesApi.getMinistries(),
  });

  // Fetch Schemes list
  const { data: schemesRes, isLoading } = useQuery({
    queryKey: ["adminSchemes", { search: searchTerm, category: categoryFilter }],
    queryFn: () =>
      schemesApi.listSchemes({
        search: searchTerm || undefined,
        category: categoryFilter || undefined,
        page_size: 50,
      }),
  });

  const categories = catRes?.data || [];
  const ministries = ministryRes?.data || [];
  const schemes = schemesRes?.data?.results || [];

  // Create Scheme Mutation
  const createMutation = useMutation({
    mutationFn: (data: Record<string, any>) => schemesApi.createScheme(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminSchemes"] });
      setIsCreateModalOpen(false);
      setFormData({
        name: "",
        short_title: "",
        category: "",
        ministry: "",
        scheme_type: "CENTRAL_SECTOR",
        description: "",
        version: "1.0",
        official_source_url: "",
        official_application_url: "",
        status: "ACTIVE",
      });
    },
  });

  // Delete Scheme Mutation
  const deleteMutation = useMutation({
    mutationFn: (schemeId: string) => schemesApi.deleteScheme(schemeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminSchemes"] });
    },
  });

  // Create Rule Mutation
  const createRuleMutation = useMutation({
    mutationFn: (data: Record<string, any>) => schemesApi.createEligibilityRule(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminSchemes"] });
      setIsRuleModalOpen(false);
    },
  });

  const handleCreateScheme = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(formData);
  };

  const handleAddRule = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedScheme) return;
    createRuleMutation.mutate({
      ...ruleFormData,
      scheme: selectedScheme.id,
    });
  };

  return (
    <div style={{ padding: "2rem", height: "100%", overflowY: "auto" }}>
      {/* Header */}
      <div style={{ marginBottom: "2rem", display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "0 0 0.4rem" }}>
            🏛️ Government Scheme Management
          </h1>
          <p style={{ color: "var(--color-text-secondary)", fontSize: "0.9rem" }}>
            Create, edit, version, and configure structured deterministic eligibility rules for government schemes.
          </p>
        </div>
        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="btn-primary"
          style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.88rem" }}
        >
          ＋ Create New Scheme
        </button>
      </div>

      {/* Filter Bar */}
      <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        <input
          type="text"
          placeholder="🔍 Search schemes by name or code..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="input-field"
          style={{ maxWidth: "340px" }}
        />
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="input-field"
          style={{ maxWidth: "220px" }}
        >
          <option value="">All Categories ({categories.length})</option>
          {categories.map((c: any) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      {/* Schemes Table */}
      <div className="card-elevated" style={{ borderRadius: "var(--radius-xl)", overflow: "hidden", border: "1px solid var(--color-border)" }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--color-border)", textAlign: "left", background: "var(--color-bg-overlay)", color: "var(--color-text-muted)" }}>
                <th style={{ padding: "0.85rem 1rem" }}>Scheme Name</th>
                <th style={{ padding: "0.85rem 1rem" }}>Category</th>
                <th style={{ padding: "0.85rem 1rem" }}>Ministry</th>
                <th style={{ padding: "0.85rem 1rem" }}>Type</th>
                <th style={{ padding: "0.85rem 1rem" }}>Version</th>
                <th style={{ padding: "0.85rem 1rem" }}>Status</th>
                <th style={{ padding: "0.85rem 1rem", textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {schemes.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: "2.5rem", textAlign: "center", color: "var(--color-text-muted)" }}>
                    No schemes found. Click "Create New Scheme" to register a scheme.
                  </td>
                </tr>
              ) : (
                schemes.map((scheme: any) => (
                  <tr key={scheme.id} style={{ borderBottom: "1px solid var(--color-border-subtle)" }}>
                    <td style={{ padding: "0.85rem 1rem", fontWeight: 600, color: "var(--color-text-primary)" }}>
                      <div>{scheme.name}</div>
                      {scheme.short_title && (
                        <span style={{ fontSize: "0.72rem", color: "var(--color-text-muted)" }}>
                          ({scheme.short_title})
                        </span>
                      )}
                    </td>
                    <td style={{ padding: "0.85rem 1rem" }}>
                      <span className="badge badge-primary">{scheme.category?.name || "General"}</span>
                    </td>
                    <td style={{ padding: "0.85rem 1rem", color: "var(--color-text-secondary)" }}>
                      {scheme.ministry?.name || "Nodal Ministry"}
                    </td>
                    <td style={{ padding: "0.85rem 1rem" }}>
                      <span className="badge badge-accent">{scheme.scheme_type?.replace("_", " ")}</span>
                    </td>
                    <td style={{ padding: "0.85rem 1rem", color: "var(--color-text-muted)" }}>
                      v{scheme.version || "1.0"}
                    </td>
                    <td style={{ padding: "0.85rem 1rem" }}>
                      <span className="badge badge-success">{scheme.status}</span>
                    </td>
                    <td style={{ padding: "0.85rem 1rem", textAlign: "right" }}>
                      <div style={{ display: "flex", gap: "0.4rem", justifyContent: "flex-end" }}>
                        <button
                          onClick={() => {
                            setSelectedScheme(scheme);
                            setIsRuleModalOpen(true);
                          }}
                          className="btn-secondary"
                          style={{ fontSize: "0.75rem", padding: "0.3rem 0.6rem" }}
                        >
                          Rules
                        </button>
                        <button
                          onClick={() => {
                            if (confirm(`Are you sure you want to delete scheme "${scheme.name}"?`)) {
                              deleteMutation.mutate(scheme.id);
                            }
                          }}
                          className="btn-ghost"
                          style={{ fontSize: "0.75rem", padding: "0.3rem 0.6rem", color: "var(--color-danger)" }}
                        >
                          ✕
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Scheme Modal */}
      {isCreateModalOpen && (
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
          onClick={() => setIsCreateModalOpen(false)}
        >
          <div
            className="card-elevated"
            style={{ maxWidth: "680px", width: "100%", borderRadius: "var(--radius-xl)", padding: "2rem", maxHeight: "90vh", overflowY: "auto" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
              <h2 style={{ fontSize: "1.25rem", fontWeight: 700, margin: 0 }}>Register New Government Scheme</h2>
              <button onClick={() => setIsCreateModalOpen(false)} className="btn-ghost">✕</button>
            </div>

            <form onSubmit={handleCreateScheme} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "0.75rem" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                    Official Scheme Name *
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Pradhan Mantri Kisan Samman Nidhi"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="input-field"
                    required
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                    Short Title / Code
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. PM-KISAN"
                    value={formData.short_title}
                    onChange={(e) => setFormData({ ...formData, short_title: e.target.value })}
                    className="input-field"
                  />
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                    Category *
                  </label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className="input-field"
                    required
                  >
                    <option value="">Select Category</option>
                    {categories.map((c: any) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                    Nodal Ministry *
                  </label>
                  <select
                    value={formData.ministry}
                    onChange={(e) => setFormData({ ...formData, ministry: e.target.value })}
                    className="input-field"
                    required
                  >
                    <option value="">Select Ministry</option>
                    {ministries.map((m: any) => (
                      <option key={m.id} value={m.id}>
                        {m.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                    Scheme Type
                  </label>
                  <select
                    value={formData.scheme_type}
                    onChange={(e) => setFormData({ ...formData, scheme_type: e.target.value })}
                    className="input-field"
                  >
                    <option value="CENTRAL_SECTOR">Central Sector (100% Centre)</option>
                    <option value="CENTRALLY_SPONSORED">Centrally Sponsored (Cost-shared)</option>
                    <option value="STATE_GOVERNMENT">State Government Scheme</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                    Version Tag
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. 1.0, 2024 Revised"
                    value={formData.version}
                    onChange={(e) => setFormData({ ...formData, version: e.target.value })}
                    className="input-field"
                  />
                </div>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                  Scheme Description & Objective
                </label>
                <textarea
                  rows={3}
                  placeholder="Comprehensive description of target beneficiaries, objectives, and policy scope..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="input-field"
                  style={{ resize: "vertical" }}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                    Official Application Portal URL
                  </label>
                  <input
                    type="url"
                    placeholder="https://..."
                    value={formData.official_application_url}
                    onChange={(e) => setFormData({ ...formData, official_application_url: e.target.value })}
                    className="input-field"
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                    Official Guidelines Source URL
                  </label>
                  <input
                    type="url"
                    placeholder="https://..."
                    value={formData.official_source_url}
                    onChange={(e) => setFormData({ ...formData, official_source_url: e.target.value })}
                    className="input-field"
                  />
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "1rem" }}>
                <button type="button" onClick={() => setIsCreateModalOpen(false)} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" disabled={createMutation.isPending} className="btn-primary">
                  {createMutation.isPending ? "Saving..." : "Save Scheme Record"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Eligibility Rule Modal */}
      {isRuleModalOpen && selectedScheme && (
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
          onClick={() => setIsRuleModalOpen(false)}
        >
          <div
            className="card-elevated"
            style={{ maxWidth: "580px", width: "100%", borderRadius: "var(--radius-xl)", padding: "2rem" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem" }}>
              <div>
                <h3 style={{ fontSize: "1.15rem", fontWeight: 700, margin: 0 }}>Add Eligibility Rule</h3>
                <p style={{ fontSize: "0.8rem", color: "var(--color-text-muted)", margin: "0.2rem 0 0" }}>
                  Scheme: {selectedScheme.name}
                </p>
              </div>
              <button onClick={() => setIsRuleModalOpen(false)} className="btn-ghost">✕</button>
            </div>

            <form onSubmit={handleAddRule} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                    Criterion Key *
                  </label>
                  <select
                    value={ruleFormData.criterion_key}
                    onChange={(e) => setRuleFormData({ ...ruleFormData, criterion_key: e.target.value })}
                    className="input-field"
                  >
                    <option value="age">age (Age in Years)</option>
                    <option value="annual_income">annual_income (Annual ₹)</option>
                    <option value="state">state (State code / name)</option>
                    <option value="occupation">occupation (Occupation)</option>
                    <option value="social_category">social_category (General/OBC/SC/ST/EWS)</option>
                    <option value="is_bpl">is_bpl (BPL Status)</option>
                    <option value="is_student">is_student (Student Status)</option>
                    <option value="has_disability">has_disability (Disability)</option>
                    <option value="land_holding_acres">land_holding_acres (Acres)</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                    Operator *
                  </label>
                  <select
                    value={ruleFormData.operator}
                    onChange={(e) => setRuleFormData({ ...ruleFormData, operator: e.target.value })}
                    className="input-field"
                  >
                    <option value="EQUALS">EQUALS (=)</option>
                    <option value="NOT_EQUALS">NOT EQUALS (≠)</option>
                    <option value="LTE">LTE (≤ Less Than or Equal)</option>
                    <option value="GTE">GTE (≥ Greater Than or Equal)</option>
                    <option value="LESS_THAN">LESS THAN (&lt;)</option>
                    <option value="GREATER_THAN">GREATER THAN (&gt;)</option>
                    <option value="IN_LIST">IN LIST (Multiple values)</option>
                    <option value="BOOLEAN_TRUE">BOOLEAN TRUE</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                  Expected Value *
                </label>
                <input
                  type="text"
                  placeholder="e.g. 25 or 250000 or Bihar"
                  value={ruleFormData.value}
                  onChange={(e) => setRuleFormData({ ...ruleFormData, value: e.target.value })}
                  className="input-field"
                  required
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: "0.25rem" }}>
                  Rule Description (Explanation for Citizen)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Applicant age must not exceed 25 years"
                  value={ruleFormData.rule_description}
                  onChange={(e) => setRuleFormData({ ...ruleFormData, rule_description: e.target.value })}
                  className="input-field"
                />
              </div>

              <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
                <label style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.82rem", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={ruleFormData.is_mandatory}
                    onChange={(e) => setRuleFormData({ ...ruleFormData, is_mandatory: e.target.checked })}
                  />
                  Mandatory Requirement (Failing disqualifies)
                </label>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "1rem" }}>
                <button type="button" onClick={() => setIsRuleModalOpen(false)} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" disabled={createRuleMutation.isPending} className="btn-primary">
                  {createRuleMutation.isPending ? "Adding..." : "Add Rule"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
