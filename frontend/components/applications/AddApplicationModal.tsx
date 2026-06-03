"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { X, Loader2 } from "lucide-react";
import { api, Application } from "@/lib/api";

const SOURCES = [
  { value: "linkedin", label: "LinkedIn" },
  { value: "company_site", label: "Company Website" },
  { value: "referral", label: "Referral" },
  { value: "job_board", label: "Job Board (Indeed, etc.)" },
  { value: "recruiter_reach", label: "Recruiter Outreach" },
  { value: "cold_apply", label: "Cold Apply" },
];

const CATEGORIES = ["PM", "APM", "TPM", "AI-PM", "GPM", "CPO", "Other"];
const LEVELS = ["junior", "mid", "senior", "staff", "principal", "director"];

interface AddApplicationModalProps {
  onClose: () => void;
  onAdded: (app: Application) => void;
}

export function AddApplicationModal({ onClose, onAdded }: AddApplicationModalProps) {
  const { getToken } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState({
    company_name: "",
    role_title: "",
    role_category: "PM",
    role_level: "senior",
    job_url: "",
    application_source: "linkedin",
    has_referral: false,
    referral_contact: "",
    notes: "",
    is_dream_role: false,
    priority: "medium" as "low" | "medium" | "high",
    expected_salary_min: "",
    expected_salary_max: "",
  });

  const set = (field: string, value: unknown) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = async () => {
    if (!form.company_name || !form.role_title) {
      setError("Company name and role title are required.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const token = await getToken();
      if (!token) throw new Error("Not authenticated");

      const payload = {
        ...form,
        expected_salary_min: form.expected_salary_min ? parseInt(form.expected_salary_min) : undefined,
        expected_salary_max: form.expected_salary_max ? parseInt(form.expected_salary_max) : undefined,
      };

      const resp = await api.createApplication(token, payload);
      if (resp.data) {
        onAdded(resp.data);
      }
    } catch (e: unknown) {
      const err = e as { message?: string };
      setError(err.message || "Failed to add application");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="w-full max-w-lg bg-gray-950 border border-gray-800 rounded-2xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <h2 className="text-lg font-semibold text-white">Log Application</h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-500 hover:text-gray-300 hover:bg-gray-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4 max-h-[70vh] overflow-y-auto">
          {error && (
            <div className="p-3 bg-red-950/50 border border-red-500/30 rounded-lg text-sm text-red-300">
              {error}
            </div>
          )}

          {/* Company + Role */}
          <div className="grid grid-cols-2 gap-3">
            <Field label="Company *">
              <input
                type="text"
                placeholder="e.g. Google"
                value={form.company_name}
                onChange={(e) => set("company_name", e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label="Role Title *">
              <input
                type="text"
                placeholder="e.g. Product Manager"
                value={form.role_title}
                onChange={(e) => set("role_title", e.target.value)}
                className={inputClass}
              />
            </Field>
          </div>

          {/* Category + Level */}
          <div className="grid grid-cols-2 gap-3">
            <Field label="Role Category">
              <select
                value={form.role_category}
                onChange={(e) => set("role_category", e.target.value)}
                className={inputClass}
              >
                {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </Field>
            <Field label="Level">
              <select
                value={form.role_level}
                onChange={(e) => set("role_level", e.target.value)}
                className={inputClass}
              >
                {LEVELS.map((l) => (
                  <option key={l} value={l}>
                    {l.charAt(0).toUpperCase() + l.slice(1)}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          {/* Source */}
          <Field label="How did you find this role?">
            <select
              value={form.application_source}
              onChange={(e) => set("application_source", e.target.value)}
              className={inputClass}
            >
              {SOURCES.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </Field>

          {/* Referral */}
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="has_referral"
              checked={form.has_referral}
              onChange={(e) => set("has_referral", e.target.checked)}
              className="w-4 h-4 rounded border-gray-700"
            />
            <label htmlFor="has_referral" className="text-sm text-gray-300">
              I have a referral
            </label>
          </div>

          {form.has_referral && (
            <Field label="Referral Contact">
              <input
                type="text"
                placeholder="Contact name or relationship"
                value={form.referral_contact}
                onChange={(e) => set("referral_contact", e.target.value)}
                className={inputClass}
              />
            </Field>
          )}

          {/* Job URL */}
          <Field label="Job URL (optional)">
            <input
              type="url"
              placeholder="https://..."
              value={form.job_url}
              onChange={(e) => set("job_url", e.target.value)}
              className={inputClass}
            />
          </Field>

          {/* Compensation */}
          <div className="grid grid-cols-2 gap-3">
            <Field label="Expected Min ($)">
              <input
                type="number"
                placeholder="e.g. 150000"
                value={form.expected_salary_min}
                onChange={(e) => set("expected_salary_min", e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label="Expected Max ($)">
              <input
                type="number"
                placeholder="e.g. 200000"
                value={form.expected_salary_max}
                onChange={(e) => set("expected_salary_max", e.target.value)}
                className={inputClass}
              />
            </Field>
          </div>

          {/* Flags */}
          <div className="flex items-center gap-6">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.is_dream_role}
                onChange={(e) => set("is_dream_role", e.target.checked)}
                className="w-4 h-4 rounded"
              />
              <span className="text-sm text-gray-300">Dream role ⭐</span>
            </label>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-400">Priority:</span>
              {["low", "medium", "high"].map((p) => (
                <button
                  key={p}
                  onClick={() => set("priority", p)}
                  className={`text-xs px-2 py-1 rounded transition-colors ${
                    form.priority === p
                      ? "bg-violet-600 text-white"
                      : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          {/* Notes */}
          <Field label="Notes (optional)">
            <textarea
              placeholder="Any context, thoughts, or details..."
              value={form.notes}
              onChange={(e) => set("notes", e.target.value)}
              rows={3}
              className={`${inputClass} resize-none`}
            />
          </Field>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-800">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Adding...
              </>
            ) : (
              "Log Application"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

const inputClass =
  "w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-violet-500 transition-colors";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-medium text-gray-400">{label}</label>
      {children}
    </div>
  );
}
