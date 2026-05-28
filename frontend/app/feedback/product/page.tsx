"use client";

import { useState } from "react";
import { useAuth, useUser } from "@clerk/nextjs";
import { Zap, ArrowRight, CheckCircle2, Loader2 } from "lucide-react";
import Link from "next/link";

export default function ProductFeedbackPage() {
  const { getToken } = useAuth();
  const { user } = useUser();
  const [step, setStep] = useState<"form" | "thanks">("form");
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    nps: "",
    working_well: "",
    missing: "",
    would_pay: "",
  });

  const set = (k: string, v: string) => setForm(p => ({ ...p, [k]: v }));

  const submit = async () => {
    if (!form.nps && !form.working_well && !form.missing) return;
    setSubmitting(true);
    try {
      const token = await getToken();
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/feedback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          email: user?.primaryEmailAddress?.emailAddress || "",
          name: user?.fullName || "",
          nps: form.nps,
          biggest_struggle: form.missing,
          would_pay: form.would_pay,
          pain_points: form.working_well ? [`Working well: ${form.working_well}`] : [],
          submitted_at: new Date().toISOString(),
        }),
      });
    } catch {
      // fall through
    } finally {
      setSubmitting(false);
      setStep("thanks");
    }
  };

  if (step === "thanks") {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
        <div className="max-w-sm text-center">
          <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-5">
            <CheckCircle2 className="w-8 h-8 text-green-400" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Thanks{user?.firstName ? `, ${user.firstName}` : ""}!</h2>
          <p className="text-gray-400 text-sm leading-relaxed mb-6">
            Your feedback goes directly to the founder and shapes what gets built next.
          </p>
          <Link href="/dashboard"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium rounded-xl transition-colors">
            Back to Dashboard <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 px-4 py-12">
      <div className="max-w-lg mx-auto">

        {/* Header */}
        <div className="text-center mb-10">
          <Link href="/dashboard" className="flex items-center gap-2 justify-center mb-6">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold text-white">CareerOS</span>
          </Link>
          <h1 className="text-2xl font-bold text-white">Shape what we build next</h1>
          <p className="text-gray-400 mt-2 text-sm leading-relaxed">
            You're one of our earliest users. Your input goes directly to the founder and directly shapes the roadmap.
          </p>
        </div>

        <div className="space-y-5">

          {/* NPS */}
          <Card title="How would you rate CareerOS so far? (1 = terrible, 10 = love it)">
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

          {/* What's working */}
          <Card title="What's been most useful so far?">
            <textarea
              value={form.working_well}
              onChange={e => set("working_well", e.target.value)}
              placeholder="e.g. The recruiter perception score helped me understand gaps I didn't know I had..."
              rows={3}
              className={textarea}
            />
          </Card>

          {/* What's missing */}
          <Card title="What's the #1 thing we should build next?">
            <textarea
              value={form.missing}
              onChange={e => set("missing", e.target.value)}
              placeholder="e.g. Auto-fix my resume based on the analysis gaps..."
              rows={3}
              className={textarea}
            />
          </Card>

          {/* Would pay more */}
          <Card title="If we built auto-fix (AI rewrites your resume based on gaps) — would you pay for it?">
            <div className="grid grid-cols-3 gap-2">
              {[
                { value: "yes_definitely", label: "Yes, definitely" },
                { value: "yes_maybe", label: "Probably yes" },
                { value: "no", label: "No / not sure" },
              ].map(opt => (
                <button key={opt.value} onClick={() => set("would_pay", opt.value)}
                  className={`py-2.5 px-2 rounded-xl text-xs font-medium border transition-all text-center ${
                    form.would_pay === opt.value
                      ? "bg-violet-600 border-violet-500 text-white"
                      : "bg-gray-800 border-gray-700 text-gray-300 hover:border-gray-600"
                  }`}>
                  {opt.label}
                </button>
              ))}
            </div>
          </Card>

          <button
            onClick={submit}
            disabled={submitting || (!form.nps && !form.working_well && !form.missing)}
            className="w-full py-3.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white font-semibold rounded-xl transition-colors flex items-center justify-center gap-2">
            {submitting
              ? <><Loader2 className="w-4 h-4 animate-spin" /> Sending...</>
              : <>Send Feedback <ArrowRight className="w-4 h-4" /></>}
          </button>

          <p className="text-xs text-center text-gray-600">
            Your feedback goes straight to the founder — no support ticket, no black hole.
          </p>
        </div>
      </div>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <p className="text-sm font-medium text-gray-200 mb-4">{title}</p>
      {children}
    </div>
  );
}

const textarea = "w-full px-3 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-violet-500 transition-colors resize-none";
