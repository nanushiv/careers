"use client";

import { useEffect, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Check, Zap, Loader2, Lock, Sparkles, CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

const FREE_FEATURES = [
  "5 AI analyses per month",
  "Track up to 10 applications",
  "ATS score + keyword gaps",
  "Basic pipeline kanban",
  "Follow-up reminders",
  "Basic resume analytics",
];

const PRO_FEATURES = [
  "Unlimited AI analyses",
  "Unlimited applications",
  "Recruiter perception analysis",
  "PM readiness scoring",
  "AI Job Matches — ranked by resume fit",
  "Outreach Drafter — personalized cold emails",
  "AI contact suggestions for networking",
  "Interview question generator",
  "Weekly AI strategy insights",
  "Full analytics + score trends",
  "Priority support",
];

declare global {
  interface Window { Razorpay: any; }
}

export default function PricingPage() {
  const { getToken, isSignedIn } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [cancelLoading, setCancelLoading] = useState(false);
  const [userPlan, setUserPlan] = useState<string>("free");
  const [cancelConfirm, setCancelConfirm] = useState(false);
  const [cancelledMsg, setCancelledMsg] = useState(false);
  const [upgraded, setUpgraded] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const rzpScriptLoaded = useRef(false);

  // Load Razorpay checkout.js once
  useEffect(() => {
    if (rzpScriptLoaded.current) return;
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    document.body.appendChild(script);
    rzpScriptLoaded.current = true;
  }, []);

  useEffect(() => {
    const init = async () => {
      const token = await getToken();
      if (!token) return;
      const resp = await api.getMe(token);
      if (resp.data?.plan) setUserPlan(resp.data.plan);
    };
    if (isSignedIn) init();
  }, [getToken, isSignedIn]);

  const handleUpgrade = async () => {
    if (!isSignedIn) { router.push("/sign-up"); return; }
    setLoading(true);
    try {
      const token = await getToken();
      const resp = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/billing/create-subscription`,
        { method: "POST", headers: { Authorization: `Bearer ${token}` } }
      );
      const data = await resp.json();
      if (!data.success) throw new Error(data.detail || "Failed to start checkout");

      const { subscription_id, key_id, name, description, prefill } = data.data;

      const rzp = new window.Razorpay({
        key: key_id,
        subscription_id,
        name,
        description,
        prefill,
        theme: { color: "#7c3aed" },
        modal: { ondismiss: () => setLoading(false) },
        handler: async (response: {
          razorpay_payment_id: string;
          razorpay_subscription_id: string;
          razorpay_signature: string;
        }) => {
          try {
            const verifyResp = await fetch(
              `${process.env.NEXT_PUBLIC_API_URL}/billing/verify-payment`,
              {
                method: "POST",
                headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
                body: JSON.stringify(response),
              }
            );
            const verifyData = await verifyResp.json();
            if (verifyData.success) {
              setUserPlan("pro");
              setUpgraded(true);
            } else {
              alert("Payment received but verification failed. Contact support — you will not be charged twice.");
            }
          } finally {
            setLoading(false);
          }
        },
      });
      rzp.open();
    } catch (e: any) {
      console.error(e);
      setErrorMsg(e?.message || "Something went wrong. Check console.");
      setLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!cancelConfirm) { setCancelConfirm(true); return; }
    setCancelLoading(true);
    try {
      const token = await getToken();
      const resp = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/billing/cancel`,
        { method: "POST", headers: { Authorization: `Bearer ${token}` } }
      );
      if (resp.ok) { setCancelledMsg(true); setCancelConfirm(false); }
    } catch (e) { console.error(e); }
    finally { setCancelLoading(false); }
  };

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center px-6 py-16">
      {/* Logo */}
      <div className="text-center mb-12">
        <Link href="/dashboard" className="flex items-center gap-2 justify-center mb-8">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <span className="text-lg font-bold text-white">CareerOS</span>
        </Link>
        <h1 className="text-4xl font-bold text-white">Simple, honest pricing</h1>
        <p className="text-gray-400 mt-3 max-w-md mx-auto">
          Start free. Upgrade when you&apos;re serious about landing your next PM role.
        </p>
      </div>

      {/* Upgrade success banner */}
      {upgraded && (
        <div className="flex items-center gap-3 px-5 py-4 mb-6 bg-emerald-950/40 border border-emerald-500/30 rounded-xl w-full max-w-3xl">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-emerald-300">You&apos;re now on Pro!</p>
            <p className="text-xs text-emerald-400/70 mt-0.5">All features unlocked. Welcome aboard.</p>
          </div>
          <Link href="/dashboard" className="text-xs text-emerald-400 hover:text-emerald-300 underline shrink-0">
            Go to Dashboard →
          </Link>
        </div>
      )}

      {/* Error banner */}
      {errorMsg && (
        <div className="flex items-center gap-3 px-5 py-4 mb-6 bg-red-950/40 border border-red-500/30 rounded-xl w-full max-w-3xl">
          <p className="text-sm text-red-300">{errorMsg}</p>
          <button onClick={() => setErrorMsg("")} className="ml-auto text-red-400 hover:text-red-200 text-xs">✕</button>
        </div>
      )}

      {/* Plans */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-3xl">
        {/* Free */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-7">
          <p className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Free</p>
          <div className="mt-3 mb-6">
            <span className="text-4xl font-bold text-white">₹0</span>
            <span className="text-gray-400 ml-1">/month</span>
          </div>
          <ul className="space-y-3 mb-8">
            {FREE_FEATURES.map(f => (
              <li key={f} className="flex items-center gap-3 text-sm text-gray-300">
                <Check className="w-4 h-4 text-gray-500 shrink-0" />{f}
              </li>
            ))}
          </ul>
          {/* Blurred pro teaser */}
          <div className="mb-6 rounded-xl border border-dashed border-violet-500/30 bg-violet-500/5 overflow-hidden">
            <div className="px-4 pt-3 pb-1 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-violet-400" />
              <p className="text-xs font-semibold text-violet-400">Pro preview — Outreach Drafter</p>
            </div>
            <div className="relative px-4 pb-4">
              <div className="mt-2 p-3 bg-gray-800/60 rounded-lg select-none" style={{ filter: "blur(3.5px)", pointerEvents: "none" }}>
                <p className="text-xs text-gray-400 mb-0.5">Subject</p>
                <p className="text-xs font-medium text-gray-200 mb-2">Loved your work on Stripe&#39;s PM onboarding</p>
                <p className="text-xs text-gray-300 leading-relaxed">
                  Hi Sarah, your recent post on scaling PM teams resonated — I&#39;ve done similar work reducing time-to-first-value by 40% at my last role. Would you have 20 minutes?
                </p>
              </div>
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-950/80 backdrop-blur-sm rounded-full border border-violet-500/30">
                  <Lock className="w-3 h-3 text-violet-400" />
                  <span className="text-xs font-medium text-violet-300">Unlock with Pro</span>
                </div>
              </div>
            </div>
          </div>
          <Link href={isSignedIn ? "/dashboard" : "/sign-up"}
            className="block w-full py-3 text-center text-sm font-medium text-gray-300 border border-gray-700 rounded-xl hover:bg-gray-800 transition-colors">
            {!isSignedIn ? "Get Started Free" : userPlan === "free" ? "Current Plan" : ""}
          </Link>
          {/* Downgrade flow */}
          {isSignedIn && userPlan === "pro" && (
            <div className="mt-3 space-y-2">
              {cancelledMsg ? (
                <p className="text-xs text-center text-amber-400 leading-relaxed">
                  Cancelled. You keep Pro until end of current billing period.
                </p>
              ) : (
                <>
                  <button onClick={handleCancel} disabled={cancelLoading}
                    className="w-full py-2.5 text-xs font-medium text-gray-500 hover:text-red-400 border border-transparent hover:border-red-500/20 rounded-xl transition-colors">
                    {cancelLoading ? "Cancelling..." : cancelConfirm ? "Confirm — cancel Pro?" : "Downgrade to Free"}
                  </button>
                  {cancelConfirm && (
                    <button onClick={() => setCancelConfirm(false)} className="w-full text-xs text-center text-gray-600 hover:text-gray-400">
                      Never mind, keep Pro
                    </button>
                  )}
                </>
              )}
            </div>
          )}
        </div>

        {/* Pro */}
        <div className="bg-violet-950/40 border-2 border-violet-500 rounded-2xl p-7 relative">
          <div className="absolute -top-3 left-1/2 -translate-x-1/2">
            <span className="px-3 py-1 bg-violet-600 text-white text-xs font-bold rounded-full uppercase tracking-wider">
              Most Popular
            </span>
          </div>
          <p className="text-sm font-semibold text-violet-400 uppercase tracking-wider">Pro</p>
          <div className="mt-3 mb-1">
            <span className="text-4xl font-bold text-white">₹999</span>
            <span className="text-gray-400 ml-1">/month</span>
          </div>
          <p className="text-xs text-gray-500 mb-6">Pay via UPI, card, net banking, or wallet</p>
          <ul className="space-y-3 mb-8">
            {PRO_FEATURES.map(f => (
              <li key={f} className="flex items-center gap-3 text-sm text-gray-200">
                <Check className="w-4 h-4 text-violet-400 shrink-0" />{f}
              </li>
            ))}
          </ul>
          {userPlan === "pro" ? (
            <div className="py-3 text-center text-sm font-semibold text-violet-300 bg-violet-600/20 border border-violet-500/40 rounded-xl">
              Current Plan ✓
            </div>
          ) : (
            <button onClick={handleUpgrade} disabled={loading}
              className="w-full py-3 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-sm font-semibold rounded-xl transition-colors flex items-center justify-center gap-2">
              {loading ? <><Loader2 className="w-4 h-4 animate-spin" />Opening checkout...</> : "Upgrade to Pro →"}
            </button>
          )}
          <p className="text-xs text-center text-gray-500 mt-3">Cancel anytime. No lock-in.</p>
        </div>
      </div>

      {/* Payment methods */}
      <div className="mt-6 flex flex-wrap items-center justify-center gap-2 text-xs">
        <span className="text-gray-600 mr-1">Accepted:</span>
        {["UPI", "Credit Card", "Debit Card", "Net Banking", "Wallet"].map(m => (
          <span key={m} className="px-2 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-400">{m}</span>
        ))}
      </div>
      <p className="text-xs text-gray-600 mt-4">
        Secure payments via Razorpay. Questions?{" "}
        <a href="mailto:shivani27chaudhary@gmail.com" className="text-gray-400 hover:text-white">shivani27chaudhary@gmail.com</a>
      </p>
    </div>
  );
}
