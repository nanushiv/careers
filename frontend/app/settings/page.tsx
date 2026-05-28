"use client";

import { useEffect, useState } from "react";
import { useAuth, useUser, useClerk } from "@clerk/nextjs";
import { Loader2, Save, ExternalLink } from "lucide-react";
import { api } from "@/lib/api";

const TARGET_ROLES = [
  "Product Manager", "Senior PM", "Associate PM (APM)",
  "AI Product Manager", "Technical PM (TPM)",
  "Group PM / Director of Product", "Chief Product Officer",
  "Product Marketing Manager", "Growth Manager",
  "Strategy & Operations", "Chief of Staff", "Founder / Startup"
];

export default function SettingsPage() {
  const { getToken } = useAuth();
  const { user: clerkUser } = useUser();
  const { openUserProfile } = useClerk();
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [dbUser, setDbUser] = useState<any>(null);

  const [form, setForm] = useState({
    full_name: "",
    current_title: "",
    current_company: "",
    location: "",
    linkedin_url: "",
    target_roles: [] as string[],
    years_experience: 0,
  });

  useEffect(() => {
    const load = async () => {
      const token = await getToken();
      if (!token) return;
      const resp = await api.getMe(token);
      if (resp.data) {
        setDbUser(resp.data);
        setForm({
          full_name: resp.data.full_name || clerkUser?.fullName || "",
          current_title: (resp.data as any).current_title || "",
          current_company: (resp.data as any).current_company || "",
          location: (resp.data as any).location || "",
          linkedin_url: (resp.data as any).linkedin_url || "",
          target_roles: resp.data.target_roles || [],
          years_experience: (resp.data as any).years_experience || 0,
        });
      }
    };
    load();
  }, [getToken]);

  const set = (k: string, v: unknown) => setForm(p => ({ ...p, [k]: v }));

  const toggleRole = (role: string) => {
    setForm(p => ({
      ...p,
      target_roles: p.target_roles.includes(role)
        ? p.target_roles.filter(r => r !== role)
        : [...p.target_roles, role],
    }));
  };

  const save = async () => {
    setSaving(true);
    try {
      const token = await getToken();
      if (!token) return;
      await api.updateMe(token, form);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) { console.error(e); }
    finally { setSaving(false); }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-sm text-gray-400 mt-0.5">Manage your profile and preferences</p>
      </div>

      {/* Profile card */}
      <Card title="Profile">
        <div className="space-y-4">
          {/* Email — read-only, managed by Clerk */}
          <Field label="Email Address">
            <div className="flex items-center gap-2">
              <input value={clerkUser?.primaryEmailAddress?.emailAddress || ""} readOnly
                className={`${input} opacity-60 cursor-not-allowed flex-1`} />
              <button onClick={() => openUserProfile()}
                className="shrink-0 flex items-center gap-1 px-3 py-2 text-xs text-violet-400 hover:text-violet-300 bg-gray-800 border border-gray-700 rounded-lg transition-colors whitespace-nowrap">
                Change <ExternalLink className="w-3 h-3" />
              </button>
            </div>
            <p className="text-xs text-gray-600 mt-1">Managed by your account. Used as sender email in Outreach.</p>
          </Field>
          <Row>
            <Field label="Full Name">
              <input value={form.full_name} onChange={e => set("full_name", e.target.value)} className={input} />
            </Field>
            <Field label="Current Title">
              <input value={form.current_title} onChange={e => set("current_title", e.target.value)}
                placeholder="e.g. Senior Engineer" className={input} />
            </Field>
          </Row>
          <Row>
            <Field label="Company">
              <input value={form.current_company} onChange={e => set("current_company", e.target.value)}
                placeholder="e.g. Infosys" className={input} />
            </Field>
            <Field label="Location">
              <input value={form.location} onChange={e => set("location", e.target.value)}
                placeholder="e.g. Hyderabad" className={input} />
            </Field>
          </Row>
          <Field label="LinkedIn URL">
            <input value={form.linkedin_url} onChange={e => set("linkedin_url", e.target.value)}
              placeholder="https://linkedin.com/in/yourprofile" className={input} />
          </Field>
          <Field label="Years of Experience">
            <input type="number" value={form.years_experience}
              onChange={e => set("years_experience", parseInt(e.target.value) || 0)}
              min={0} max={30} className={input} />
          </Field>
        </div>
      </Card>

      {/* Target roles */}
      <Card title="Target Roles">
        <div className="flex flex-wrap gap-2">
          {TARGET_ROLES.map(role => (
            <button key={role} onClick={() => toggleRole(role)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-all ${
                form.target_roles.includes(role)
                  ? "bg-violet-600 border-violet-500 text-white"
                  : "bg-gray-800 border-gray-700 text-gray-300 hover:border-gray-600"
              }`}>
              {role}
            </button>
          ))}
        </div>
      </Card>

      {/* Plan info */}
      <Card title="Plan">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-200 capitalize">
              {dbUser?.plan || "Free"} Plan
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              {dbUser?.plan === "free"
                ? "5 analyses/month · 10 applications"
                : "Unlimited analyses · Unlimited applications"}
            </p>
          </div>
          {dbUser?.plan === "free" && (
            <a href="/pricing"
              className="flex items-center gap-1 px-3 py-1.5 bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium rounded-lg transition-colors">
              Upgrade <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      </Card>

      {/* Save button */}
      <button onClick={save} disabled={saving}
        className="w-full flex items-center justify-center gap-2 py-3 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white font-medium rounded-xl transition-colors">
        {saving ? <><Loader2 className="w-4 h-4 animate-spin" /> Saving...</>
          : saved ? "✅ Saved!"
          : <><Save className="w-4 h-4" /> Save Changes</>}
      </button>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <p className="text-sm font-semibold text-gray-300 mb-4">{title}</p>
      {children}
    </div>
  );
}

function Row({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-2 gap-3">{children}</div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-medium text-gray-400">{label}</label>
      {children}
    </div>
  );
}

const input = "w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-violet-500 transition-colors";
