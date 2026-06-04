"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Check, Zap, Loader2, Lock, Sparkles, ExternalLink } from "lucide-react";
import Link from "next/link";
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

export default function PricingPage() {
  const { getToken, isSignedIn } = useAuth();
  const [loading, setLoading] = useState(false);
  const [portalLoading, setPortalLoading] = useState(false);
  const [cancelLoading, setCancelLoading] = useState(false);
  const [userPlan, setUserPlan] = useState<string>("free");
  const [priceDisplay, setPriceDisplay] = useState("₹999");
  const [cancelConfirm, setCancelConfirm] = useState(false);
  const [cancelledMsg, setCancelledMsg] = useState(false);

  useEffect(() => {
    const init = async () => {
      // Fetch geo-based price
      try {
        const resp = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/billing/country`);
        const data = await resp.json();
        if (data.data?.price_display) setPriceDisplay(data.data.price_display);
      } catch { /* fallback to ₹999 */ }

      // Fetch current plan
      const token = await getToken();
      if (!token) return;
      const resp = await api.getMe(token);
      if (resp.data?.plan) setUserPlan(resp.data.plan);
    };
    if (isSignedIn) init();
    else {
      // Still fetch price for non-signed-in visitors
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/billing/country`)
        .then(r => r.json())
        .then(d => { if (d.data?.price_display) setPriceDisplay(d.data.price_display); })
        .catch(() => {});
    }
  }, [getToken, isSignedIn]);

  const handleUpgrade = async () => {
    if (!isSignedIn) { window.location.href = "/sign-up"; return; }
    setLoading(true);
    try {
      const token = await getToken();
      const resp = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/billing/create-checkout`,
        { method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" } }
      );
      const data = await resp.json();
      if (data.data?.url) window.location.href = data.data.url;
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const handlePortal = async () => {
    setPortalLoading(true);
    try {
      const token = await getToken();
      const resp = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/billing/portal`,
        { method: "POST", headers: { Authorization: `Bearer ${token}` } }
      );
      const data = await resp.json();
      if (data.data?.url) window.open(data.data.url, "_blank");
    } catch (e) { console.error(e); }
    finally { setPortalLoading(false); }
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
      if (resp.ok) {
        setCancelledMsg(true);
        setCancelConfirm(false);
      }
    } catch (e) { console.error(e); }
    finally { setCancelLoading(false); }
  };

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center px-6 py-16">
      {/* Header */}
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

      {/* Plans */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-3xl">
        {/* Free */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-7">
          <p className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Free</p>
          <div className="mt-3 mb-6">
            <span className="text-4xl font-bold text-white">$0</span>
            <span className="text-gray-400 ml-1">/month</span>
          </div>
          <ul className="space-y-3 mb-8">
            {FREE_FEATURES.map(f => (
              <li key={f} className="flex items-center gap-3 text-sm text-gray-300">
                <Check className="w-4 h-4 text-gray-500 shrink-0" />{f}
              </li>
            ))}
          </ul>
          {/* Pro teaser — locked preview */}
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
                  Hi Sarah, your recent post on scaling PM teams resonated — I&#39;ve done similar work reducing time-to-first-value by 40% at my last role. Would you have 20 minutes for a quick chat?
                </p>
              </div>
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
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
          {isSignedIn && userPlan === "pro" && (
            <div className="mt-3 space-y-2">
              {cancelledMsg ? (
                <p className="text-xs text-center text-amber-400">Your subscription will cancel at the end of the billing period.</p>
              ) : (
                <>
                  <button onClick={handleCancel} disabled={cancelLoading}
                    className="w-full py-2.5 text-center text-xs font-medium text-gray-500 hover:text-red-400 transition-colors border border-transparent hover:border-red-500/20 rounded-xl">
                    {cancelLoading ? "Cancelling..." : cancelConfirm ? "Confirm — cancel my Pro subscription?" : "Downgrade to Free"}
                  </button>
                  {cancelConfirm && (
                    <button onClick={() => setCancelConfirm(false)} className="w-full text-xs text-center text-gray-600 hover:text-gray-400">
                      Never mind
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
          <div className="mt-3 mb-6">
            <span className="text-4xl font-bold text-white">{priceDisplay}</span>
            <span className="text-gray-400 ml-1">/month</span>
          </div>
          <ul className="space-y-3 mb-8">
            {PRO_FEATURES.map(f => (
              <li key={f} className="flex items-center gap-3 text-sm text-gray-200">
                <Check className="w-4 h-4 text-violet-400 shrink-0" />{f}
              </li>
            ))}
          </ul>

          {userPlan === "pro" ? (
            <div className="space-y-3">
              <div className="w-full py-3 text-center text-sm font-semibold text-violet-300 bg-violet-600/20 border border-violet-500/40 rounded-xl">
                Current Plan ✓
              </div>
              <button onClick={handlePortal} disabled={portalLoading}
                className="w-full py-2.5 flex items-center justify-center gap-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm font-medium rounded-xl border border-gray-700 transition-colors">
                {portalLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ExternalLink className="w-4 h-4" />}
                Manage Billing
              </button>
            </div>
          ) : (
            <button onClick={handleUpgrade} disabled={loading}
              className="w-full py-3 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-sm font-semibold rounded-xl transition-colors flex items-center justify-center gap-2">
              {loading ? <><Loader2 className="w-4 h-4 animate-spin" />Processing...</> : "Upgrade to Pro →"}
            </button>
          )}
          <p className="text-xs text-center text-gray-500 mt-3">Cancel anytime. No lock-in.</p>
        </div>
      </div>

      <p className="text-xs text-gray-600 mt-8">
        Payments processed securely by Stripe. Questions?{" "}
        <a href="mailto:shivani27chaudhary@gmail.com" className="text-gray-400 hover:text-white">shivani27chaudhary@gmail.com</a>
      </p>
    </div>
  );
}
