"use client";

import { useState } from "react";
import { Zap, Star, ArrowRight, CheckCircle2, Loader2, Users, Brain, Target } from "lucide-react";

const PAIN_POINTS = [
  "Getting no callbacks despite applying everywhere",
  "Don't know if my resume is the problem",
  "Stuck in applications, not getting past screening",
  "Transitioning to PM/AI roles — don't know where to start",
  "Getting ghosted after phone screens",
  "No idea how recruiters actually see my resume",
];

const FROM_ROLES = ["Software Engineer", "Data Scientist", "Business Analyst", "Consultant", "Other Tech Role", "Non-tech background"];
const TARGET_ROLES = ["Product Manager", "AI Product Manager", "Technical PM", "Senior PM", "Group PM / CPO"];

export default function FeedbackPage() {
  const [step, setStep] = useState<"form" | "thanks">("form");
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    email: "",
    name: "",
    from_role: "",
    target_role: "",
    pain_points: [] as string[],
    would_pay: "",
    nps: "",
    biggest_struggle: "",
    linkedin_url: "",
  });

  const set = (k: string, v: unknown) => setForm(p => ({ ...p, [k]: v }));

  const togglePain = (pain: string) => {
    setForm(p => ({
      ...p,
      pain_points: p.pain_points.includes(pain)
        ? p.pain_points.filter(x => x !== pain)
        : [...p.pain_points, pain],
    }));
  };

  const submit = async () => {
    if (!form.email || !form.would_pay) return;
    setSubmitting(true);
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, submitted_at: new Date().toISOString() }),
      });
      setStep("thanks");
    } catch {
      // Still show thanks even if API fails — don't lose the signal
      setStep("thanks");
    } finally {
      setSubmitting(false);
    }
  };

  if (step === "thanks") return <ThanksScreen name={form.name} />;

  return (
    <div className="min-h-screen bg-gray-950 px-4 py-12">
      <div className="max-w-xl mx-auto">

        {/* Header */}
        <div className="text-center mb-10">
          <div className="flex items-center gap-2 justify-center mb-6">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-white">CareerOS</span>
          </div>
          <h1 className="text-3xl font-bold text-white leading-tight">
            Help us build the tool that gets you hired
          </h1>
          <p className="text-gray-400 mt-3 text-base leading-relaxed">
            We're building an AI that tells you <em>exactly</em> why you're not getting callbacks —
            and gives you a step-by-step fix. 3 minutes of your time = a better product for everyone.
          </p>

          {/* Social proof */}
          <div className="flex items-center justify-center gap-2 mt-4">
            <div className="flex -space-x-2">
              {["V", "P", "R", "A"].map((l, i) => (
                <div key={i} className="w-7 h-7 rounded-full bg-violet-600 border-2 border-gray-950 flex items-center justify-center text-xs text-white font-bold">
                  {l}
                </div>
              ))}
            </div>
            <span className="text-sm text-gray-400">124 PMs + engineers already responded</span>
          </div>

          {/* Direct contact */}
          <p className="text-xs text-gray-500 mt-3">
            Questions? Reach the founder directly at{" "}
            <a href="mailto:shivani27chaudhary@gmail.com" className="text-violet-400 hover:text-violet-300 underline">
              shivani27chaudhary@gmail.com
            </a>
          </p>
        </div>

        <div className="space-y-5">

          {/* Name + Email */}
          <Card>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Field label="Your name">
                <input value={form.name} onChange={e => set("name", e.target.value)}
                  placeholder="Priya Sharma" className={input} />
              </Field>
              <Field label="Email *">
                <input type="email" value={form.email} onChange={e => set("email", e.target.value)}
                  placeholder="you@gmail.com" className={input} />
              </Field>
            </div>
            <Field label="LinkedIn URL (optional — we won't spam)">
              <input value={form.linkedin_url} onChange={e => set("linkedin_url", e.target.value)}
                placeholder="linkedin.com/in/yourname" className={`${input} mt-3`} />
            </Field>
          </Card>

          {/* Roles */}
          <Card title="Your transition">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Field label="Coming from">
                <select value={form.from_role} onChange={e => set("from_role", e.target.value)} className={input}>
                  <option value="">Select...</option>
                  {FROM_ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </Field>
              <Field label="Targeting">
                <select value={form.target_role} onChange={e => set("target_role", e.target.value)} className={input}>
                  <option value="">Select...</option>
                  {TARGET_ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </Field>
            </div>
          </Card>

          {/* Pain points */}
          <Card title="What's your biggest pain right now? (select all that apply)">
            <div className="space-y-2">
              {PAIN_POINTS.map(pain => (
                <button key={pain} onClick={() => togglePain(pain)}
                  className={`w-full text-left px-3 py-2.5 rounded-lg text-sm border transition-all ${
                    form.pain_points.includes(pain)
                      ? "bg-violet-600/20 border-violet-500/50 text-violet-200"
                      : "bg-gray-800/60 border-gray-700 text-gray-300 hover:border-gray-600"
                  }`}>
                  {form.pain_points.includes(pain) ? "✓ " : ""}{pain}
                </button>
              ))}
            </div>
          </Card>

          {/* Biggest struggle — open text */}
          <Card title="In your own words — what's the #1 thing holding back your job search?">
            <textarea value={form.biggest_struggle} onChange={e => set("biggest_struggle", e.target.value)}
              placeholder="Be specific — this directly shapes what we build first..."
              rows={3} className={`${input} resize-none w-full`} />
          </Card>

          {/* Would pay */}
          <Card title="If CareerOS showed you exactly why you're not getting callbacks and gave you a fix — would you pay $29/month? *">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {[
                { value: "yes_definitely", label: "Yes, definitely 🙌" },
                { value: "yes_maybe", label: "Probably yes" },
                { value: "no", label: "No / not sure" },
              ].map(opt => (
                <button key={opt.value} onClick={() => set("would_pay", opt.value)}
                  className={`py-3 px-2 rounded-xl text-xs font-medium border transition-all text-center ${
                    form.would_pay === opt.value
                      ? "bg-violet-600 border-violet-500 text-white"
                      : "bg-gray-800 border-gray-700 text-gray-300 hover:border-gray-600"
                  }`}>
                  {opt.label}
                </button>
              ))}
            </div>
          </Card>

          {/* NPS */}
          <Card title="How painful is your job search right now? (1 = fine, 10 = miserable)">
            <div className="flex gap-1.5 flex-wrap">
              {[...Array(10)].map((_, i) => {
                const n = String(i + 1);
                return (
                  <button key={n} onClick={() => set("nps", n)}
                    className={`w-9 h-9 rounded-lg text-sm font-semibold border transition-all ${
                      form.nps === n
                        ? "bg-violet-600 border-violet-500 text-white"
                        : "bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600"
                    }`}>
                    {n}
                  </button>
                );
              })}
            </div>
          </Card>

          {/* Submit */}
          <button onClick={submit}
            disabled={submitting || !form.email || !form.would_pay}
            className="w-full py-4 bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white font-semibold rounded-xl transition-colors flex items-center justify-center gap-2 text-base">
            {submitting
              ? <><Loader2 className="w-4 h-4 animate-spin" /> Submitting...</>
              : <>Send Feedback <ArrowRight className="w-4 h-4" /></>}
          </button>

          <p className="text-xs text-center text-gray-600">
            No spam. We'll email you when CareerOS is ready for early access.
          </p>

        </div>
      </div>
    </div>
  );
}

function ThanksScreen({ name }: { name: string }) {
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
      <div className="max-w-md text-center">
        <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
          <CheckCircle2 className="w-10 h-10 text-green-400" />
        </div>
        <h2 className="text-3xl font-bold text-white mb-3">
          Thank you{name ? `, ${name.split(" ")[0]}` : ""}! 🎉
        </h2>
        <p className="text-gray-400 text-base leading-relaxed mb-8">
          Your feedback is invaluable. We're building CareerOS based on exactly this kind of input.
          We'll email you as soon as early access is ready.
        </p>

        {/* What's coming */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 text-left space-y-3 mb-8">
          <p className="text-sm font-semibold text-gray-300">What you'll get in early access:</p>
          {[
            { icon: Brain, text: "AI that reads your resume like a recruiter" },
            { icon: Target, text: "Exact keywords you're missing for each role" },
            { icon: Users, text: "PM readiness score across 6 dimensions" },
            { icon: Star, text: "Early access pricing (locked in for life)" },
          ].map(({ icon: Icon, text }) => (
            <div key={text} className="flex items-center gap-3">
              <Icon className="w-4 h-4 text-violet-400 shrink-0" />
              <span className="text-sm text-gray-300">{text}</span>
            </div>
          ))}
        </div>

        <p className="text-sm text-gray-500">
          Share with a friend who's job hunting? 
          <a href="https://linkedin.com" target="_blank"
            className="ml-1 text-violet-400 hover:text-violet-300 underline">
            Share on LinkedIn →
          </a>
        </p>
      </div>
    </div>
  );
}

const input = "w-full px-3 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-violet-500 transition-colors";

function Card({ title, children }: { title?: string; children: React.ReactNode }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      {title && <p className="text-sm font-medium text-gray-200 mb-4">{title}</p>}
      {children}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-medium text-gray-400">{label}</label>
      {children}
    </div>
  );
}
