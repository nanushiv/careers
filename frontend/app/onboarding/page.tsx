"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { Zap, ArrowRight, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

const TARGET_ROLES = [
  "Product Manager", "Senior PM", "Associate PM (APM)",
  "AI Product Manager", "Technical PM (TPM)",
  "Group PM / Director of Product", "Chief Product Officer",
  "Product Marketing Manager", "Growth Manager",
  "Strategy & Operations", "Chief of Staff", "Founder / Startup"
];
const EXPERIENCE_LEVELS = ["0-2 years", "3-5 years", "6-9 years", "10+ years"];

export default function OnboardingPage() {
  const { getToken } = useAuth();
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState({
    full_name: "",
    current_title: "",
    current_company: "",
    years_experience: "",
    target_roles: [] as string[],
    location: "",
  });

  const set = (k: string, v: unknown) => setForm(p => ({ ...p, [k]: v }));

  const toggleRole = (role: string) => {
    setForm(p => ({
      ...p,
      target_roles: p.target_roles.includes(role)
        ? p.target_roles.filter(r => r !== role)
        : [...p.target_roles, role],
    }));
  };

  const finish = async () => {
    setSaving(true);
    setError(null);
    try {
      const token = await getToken();
      if (!token) { setError("Not authenticated — try refreshing"); return; }
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { years_experience, ...rest } = form;
      await api.updateMe(token, {
        ...rest,
        onboarding_completed: true,
        onboarding_step: 3,
      });
      router.push("/dashboard");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-6">
      <div className="w-full max-w-lg">
        {/* Logo */}
        <div className="flex items-center gap-2 justify-center mb-10">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold text-white">CareerOS</span>
        </div>

        {/* Progress dots */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {[1, 2, 3].map(s => (
            <div key={s} className={`h-1.5 rounded-full transition-all duration-300 ${
              s === step ? "w-8 bg-violet-500" : s < step ? "w-4 bg-violet-700" : "w-4 bg-gray-700"
            }`} />
          ))}
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8">

          {/* Step 1 — Basic info */}
          {step === 1 && (
            <div className="space-y-5">
              <div>
                <h2 className="text-xl font-bold text-white">Welcome! Let's set up your profile</h2>
                <p className="text-sm text-gray-400 mt-1">This helps us personalize your career intelligence.</p>
              </div>
              <Field label="Your full name">
                <input value={form.full_name} onChange={e => set("full_name", e.target.value)}
                  placeholder="e.g. Priya Sharma" className={input} />
              </Field>
              <Field label="Current job title">
                <input value={form.current_title} onChange={e => set("current_title", e.target.value)}
                  placeholder="e.g. Software Engineer" className={input} />
              </Field>
              <Field label="Current company (optional)">
                <input value={form.current_company} onChange={e => set("current_company", e.target.value)}
                  placeholder="e.g. TCS, Infosys, Startup..." className={input} />
              </Field>
              <Field label="Location">
                <input value={form.location} onChange={e => set("location", e.target.value)}
                  placeholder="e.g. Hyderabad, India" className={input} />
              </Field>
              <button onClick={() => setStep(2)}
                disabled={!form.full_name || !form.current_title}
                className="w-full flex items-center justify-center gap-2 py-3 bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white font-medium rounded-xl transition-colors">
                Continue <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Step 2 — Target roles */}
          {step === 2 && (
            <div className="space-y-5">
              <div>
                <h2 className="text-xl font-bold text-white">What roles are you targeting?</h2>
                <p className="text-sm text-gray-400 mt-1">Select all that apply. We'll tailor your AI analysis.</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {TARGET_ROLES.map(role => (
                  <button key={role} onClick={() => toggleRole(role)}
                    className={`px-3 py-2 rounded-lg text-sm font-medium border transition-all ${
                      form.target_roles.includes(role)
                        ? "bg-violet-600 border-violet-500 text-white"
                        : "bg-gray-800 border-gray-700 text-gray-300 hover:border-gray-600"
                    }`}>
                    {role}
                  </button>
                ))}
              </div>
              <Field label="Years of experience">
                <div className="grid grid-cols-4 gap-2">
                  {EXPERIENCE_LEVELS.map(lvl => (
                    <button key={lvl} onClick={() => set("years_experience", lvl)}
                      className={`py-2 rounded-lg text-xs font-medium border transition-all ${
                        form.years_experience === lvl
                          ? "bg-violet-600 border-violet-500 text-white"
                          : "bg-gray-800 border-gray-700 text-gray-300"
                      }`}>
                      {lvl}
                    </button>
                  ))}
                </div>
              </Field>
              <div className="flex gap-3">
                <button onClick={() => setStep(1)}
                  className="flex-1 py-3 border border-gray-700 text-gray-300 rounded-xl hover:bg-gray-800 transition-colors text-sm">
                  Back
                </button>
                <button onClick={() => setStep(3)}
                  disabled={form.target_roles.length === 0}
                  className="flex-1 flex items-center justify-center gap-2 py-3 bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white font-medium rounded-xl transition-colors">
                  Continue <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* Step 3 — Ready */}
          {step === 3 && (
            <div className="space-y-5 text-center">
              <div className="w-16 h-16 bg-violet-500/20 rounded-2xl flex items-center justify-center mx-auto">
                <Zap className="w-8 h-8 text-violet-400" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">You're all set, {form.full_name.split(" ")[0]}!</h2>
                <p className="text-sm text-gray-400 mt-2">
                  Upload your resume to get your first AI analysis — ATS score, recruiter perception, and a personalized improvement roadmap.
                </p>
              </div>
              <div className="bg-gray-800/60 rounded-xl p-4 text-left space-y-2">
                <p className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Your setup</p>
                <p className="text-sm text-gray-300">🎯 Targeting: <span className="text-violet-300">{form.target_roles.join(", ")}</span></p>
                <p className="text-sm text-gray-300">📍 Location: <span className="text-violet-300">{form.location || "Not set"}</span></p>
                <p className="text-sm text-gray-300">⚡ Experience: <span className="text-violet-300">{form.years_experience || "Not set"}</span></p>
              </div>
              {error && (
                <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">{error}</p>
              )}
              <div className="flex gap-3">
                <button onClick={() => setStep(2)}
                  className="flex-1 py-3 border border-gray-700 text-gray-300 rounded-xl hover:bg-gray-800 transition-colors text-sm">
                  Back
                </button>
                <button onClick={finish} disabled={saving}
                  className="flex-1 flex items-center justify-center gap-2 py-3 bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white font-medium rounded-xl transition-colors">
                  {saving ? <><Loader2 className="w-4 h-4 animate-spin" /> Saving...</> : <>Go to Dashboard <ArrowRight className="w-4 h-4" /></>}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const input = "w-full px-3 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-violet-500 transition-colors";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-medium text-gray-400">{label}</label>
      {children}
    </div>
  );
}
