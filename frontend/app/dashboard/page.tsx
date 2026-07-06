"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { motion } from "framer-motion";
import {
  TrendingUp, AlertCircle, CheckCircle2, Clock,
  ArrowRight, Plus, Briefcase, FileText, Brain, Sparkles, X
} from "lucide-react";
import Link from "next/link";
import { api, DashboardData, ApiError } from "@/lib/api";
import { CareerHealthGauge } from "@/components/dashboard/CareerHealthGauge";
import { InsightCard } from "@/components/dashboard/InsightCard";
import { PipelineMini } from "@/components/dashboard/PipelineMini";
import { ApplicationCard } from "@/components/applications/ApplicationCard";
import { StageDistribution } from "@/components/dashboard/StageDistribution";
import { ResumeNudgeBanner } from "@/components/dashboard/ResumeNudgeBanner";

const STAGES = ["applied", "screening", "phone_screen", "technical", "case_study", "final", "offer"];

export default function DashboardPage() {
  const { getToken } = useAuth();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [latestAnalysis, setLatestAnalysis] = useState<any>(null);
  const [insights, setInsights] = useState<any[]>([]);
  const [generatingInsights, setGeneratingInsights] = useState(false);
  const [insightsTakingLong, setInsightsTakingLong] = useState(false);
  const [showUpgradeBanner, setShowUpgradeBanner] = useState(false);

  useEffect(() => {
    if (searchParams.get("upgraded") === "true") {
      setShowUpgradeBanner(true);
      // Remove the query param from URL without re-render
      router.replace("/dashboard", { scroll: false });
    }
  }, [searchParams, router]);

  const load = async (isRetry = false, attempt = 1) => {
    try {
      if (isRetry) setRetrying(true);
      const token = await getToken();
      if (!token) {
        setError("Session expired — please sign out and sign back in.");
        setLoading(false);
        setRetrying(false);
        return;
      }
      const resp = await api.getDashboard(token);
      const analysisResp = await api.listAnalyses(token, { analysis_type: "ats" }).catch(() => ({ data: [] as any[] }));
      if (analysisResp.data?.[0]) setLatestAnalysis(analysisResp.data[0]);
      if (resp.data) {
        setData(resp.data);
        setInsights(resp.data.insights ?? []);
        setError(null);
      }
      setLoading(false);
      setRetrying(false);
    } catch (e) {
      console.error("Dashboard load error:", e);
      if (e instanceof ApiError) {
        if (e.status === 404) {
          router.replace("/onboarding");
          return;
        }
        if (e.status === 401) {
          setError("Session expired — please sign out and sign back in.");
          setLoading(false);
          setRetrying(false);
          return;
        }
        setError(`Error ${e.status}: ${e.message}`);
        setLoading(false);
        setRetrying(false);
        return;
      }
      const msg = e instanceof Error ? e.message : String(e);
      const isAborted = msg.toLowerCase().includes("abort") || msg.toLowerCase().includes("timeout");
      const isNetwork = isAborted || msg.toLowerCase().includes("load") || msg.toLowerCase().includes("fetch") || msg.toLowerCase().includes("network");
      if (isNetwork && attempt < 4) {
        setTimeout(() => load(false, attempt + 1), attempt * 2000);
        return;
      }
      setError(isNetwork ? "Server is not responding — please tap Retry." : msg);
      setLoading(false);
      setRetrying(false);
    }
  };

  useEffect(() => { load(); }, [getToken]);

  if (loading) return <DashboardSkeleton />;
  if (error || !data) return <ErrorState message={error || "No data"} onRetry={() => load(true)} retrying={retrying} />;

  const { career_health_score, pipeline_summary, follow_ups, resumes, recent_applications } = data;

  const isNewUser = (resumes?.length ?? 0) === 0 && recent_applications.length === 0;

  const handleGenerateInsights = async () => {
    setGeneratingInsights(true);
    try {
      const token = await getToken();
      if (!token) return;
      await api.generateInsights(token);
      // Poll for new insights
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        if (attempts === 5) setInsightsTakingLong(true);
        try {
          const resp = await api.listInsights(token);
          if (resp.error) { clearInterval(poll); setGeneratingInsights(false); setInsightsTakingLong(false); return; }
          if (resp.data && resp.data.length > 0) {
            setInsights(resp.data);
            setGeneratingInsights(false);
            setInsightsTakingLong(false);
            clearInterval(poll);
          }
        } catch { clearInterval(poll); setGeneratingInsights(false); setInsightsTakingLong(false); }
        if (attempts >= 15) {
          setGeneratingInsights(false);
          setInsightsTakingLong(false);
          clearInterval(poll);
        }
      }, 3000);
    } catch {
      setGeneratingInsights(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {showUpgradeBanner && (
        <div className="flex items-center gap-3 px-5 py-4 bg-emerald-950/40 border border-emerald-500/30 rounded-xl">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-emerald-300">Welcome to CareerOS Pro!</p>
            <p className="text-xs text-emerald-400/70 mt-0.5">All Pro features are now unlocked — job matches, outreach drafter, unlimited analyses.</p>
          </div>
          <button onClick={() => setShowUpgradeBanner(false)} className="text-emerald-600 hover:text-emerald-400">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
      {isNewUser && <GettingStartedBanner />}
      {!isNewUser && latestAnalysis && (
        <ResumeNudgeBanner
          score={latestAnalysis.overall_score ?? 0}
          topGaps={(latestAnalysis.gaps ?? []).map((g: any) => g.description).filter(Boolean)}
          resumeId={latestAnalysis.resume_id}
          analysisDate={latestAnalysis.created_at}
        />
      )}
      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Career Dashboard
          </h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Your hiring intelligence hub
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/resume?action=analyze"
            className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <Brain className="w-4 h-4" />
            Analyze Resume
          </Link>
          <Link
            href="/applications?action=add"
            className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 text-sm font-medium rounded-lg transition-colors border border-gray-700"
          >
            <Plus className="w-4 h-4" />
            Log Application
          </Link>
        </div>
      </div>

      {/* ── Top Row: Health + Stats ──────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Career Health Score */}
        <div className={`lg:col-span-1 rounded-xl p-6 flex flex-col items-center border transition-colors ${
          career_health_score >= 65
            ? "bg-green-950/20 border-green-500/20"
            : career_health_score >= 50
            ? "bg-amber-950/20 border-amber-500/20"
            : "bg-gray-900 border-gray-800"
        }`}>
          <p className="text-sm font-medium text-gray-400 mb-4">Career Health</p>
          <CareerHealthGauge score={career_health_score} />
        </div>

        {/* Stats */}
        <div className="lg:col-span-3 grid grid-cols-2 sm:grid-cols-4 gap-4">
          <StatCard
            label="Total Applied"
            value={pipeline_summary.total}
            icon={Briefcase}
            color="blue"
          />
          <StatCard
            label="Active Pipeline"
            value={pipeline_summary.active}
            icon={TrendingUp}
            color="violet"
          />
          <StatCard
            label="Callback Rate"
            value={`${pipeline_summary.callback_rate}%`}
            icon={CheckCircle2}
            color={pipeline_summary.callback_rate >= 15 ? "green" : "yellow"}
          />
          <StatCard
            label="This Week"
            value={pipeline_summary.this_week}
            icon={Clock}
            color="gray"
          />
        </div>
      </div>

      {/* ── Middle Row: Insights + Pipeline ─────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* AI Insights */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
              AI Insights
            </h2>
            <Link href="/intelligence" className="text-xs text-violet-400 hover:text-violet-300 flex items-center gap-1">
              View all <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          {insights.length === 0 ? (
            <EmptyInsights hasAnalysis={!!latestAnalysis} onGenerate={handleGenerateInsights} generating={generatingInsights} takingLong={insightsTakingLong} />
          ) : (
            insights.map((insight, i) => (
              <motion.div
                key={insight.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
              >
                <InsightCard insight={insight} />
              </motion.div>
            ))
          )}
        </div>

        {/* Stage Distribution */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">
            Pipeline
          </h2>
          <StageDistribution distribution={pipeline_summary.stage_distribution} />
          {follow_ups.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-800">
              <p className="text-xs font-medium text-gray-400 mb-2">Follow-ups Due</p>
              {follow_ups.slice(0, 3).map((fu) => (
                <div key={fu.id} className="flex items-center gap-2 py-1.5">
                  <div className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
                  <span className="text-xs text-gray-300 truncate">
                    {fu.applications?.company_name || (fu.application_id ? "Unknown" : "Outreach")} — {fu.due_date}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Bottom Row: Recent Applications ─────────────────────────── */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
            Recent Applications
          </h2>
          <Link href="/applications" className="text-xs text-violet-400 hover:text-violet-300 flex items-center gap-1">
            View all <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
        {recent_applications.length === 0 ? (
          <EmptyApplications />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {recent_applications.slice(0, 6).map((app) => (
              <ApplicationCard key={app.id} application={app} compact />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
  color: "blue" | "violet" | "green" | "yellow" | "gray";
}) {
  const colors = {
    blue: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    violet: "bg-violet-500/10 text-violet-400 border-violet-500/20",
    green: "bg-green-500/10 text-green-400 border-green-500/20",
    yellow: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    gray: "bg-gray-800 text-gray-400 border-gray-700",
  };

  return (
    <div className={`rounded-xl p-4 border ${colors[color]}`}>
      <Icon className="w-4 h-4 mb-2 opacity-70" />
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-xs text-gray-400 mt-0.5">{label}</p>
    </div>
  );
}

function GettingStartedBanner() {
  const steps = [
    { num: 1, label: "Upload your resume", href: "/resume", cta: "Go to Resume Vault" },
    { num: 2, label: "Run AI analysis to get your ATS score", href: "/resume", cta: "Run Analysis" },
    { num: 3, label: "Log your first job application", href: "/applications?action=add", cta: "Add Application" },
  ];
  return (
    <div className="bg-gradient-to-r from-violet-950/40 to-blue-950/30 border border-violet-500/20 rounded-xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <Sparkles className="w-5 h-5 text-violet-400" />
        <p className="font-semibold text-white">Welcome to CareerOS — let&apos;s get you set up</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {steps.map(s => (
          <Link key={s.num} href={s.href}
            className="flex items-center gap-3 p-3 bg-gray-900/60 border border-gray-700 rounded-lg hover:border-violet-500/40 transition-all group">
            <div className="w-7 h-7 rounded-full bg-violet-600/20 border border-violet-500/30 flex items-center justify-center shrink-0 text-xs font-bold text-violet-400">
              {s.num}
            </div>
            <div className="min-w-0">
              <p className="text-xs text-gray-300 leading-tight">{s.label}</p>
              <p className="text-xs text-violet-400 mt-0.5 group-hover:text-violet-300">{s.cta} →</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

function EmptyInsights({ hasAnalysis, onGenerate, generating, takingLong }: { hasAnalysis: boolean; onGenerate: () => void; generating: boolean; takingLong?: boolean }) {
  return (
    <div className="bg-gray-900 border border-gray-800 border-dashed rounded-xl p-8 text-center">
      <Brain className={`w-8 h-8 mx-auto mb-3 ${generating ? "text-violet-500 animate-pulse" : "text-gray-600"}`} />
      {hasAnalysis ? (
        <>
          <p className="text-sm text-gray-400">
            {generating ? "Generating your AI insights…" : "No insights yet — generate them now based on your applications."}
          </p>
          {generating && takingLong && (
            <p className="text-xs text-gray-500 mt-1">Taking longer than expected — almost there…</p>
          )}
          {!generating && (
            <button
              onClick={onGenerate}
              className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium rounded-lg transition-colors"
            >
              <Brain className="w-4 h-4" />
              Generate Insights
            </button>
          )}
        </>
      ) : (
        <>
          <p className="text-sm text-gray-400">
            Upload a resume and run your first analysis to unlock AI insights.
          </p>
          <Link
            href="/resume"
            className="mt-3 inline-flex items-center gap-1 text-sm text-violet-400 hover:text-violet-300"
          >
            Upload Resume <ArrowRight className="w-3 h-3" />
          </Link>
        </>
      )}
    </div>
  );
}

function EmptyApplications() {
  return (
    <div className="bg-gray-900 border border-gray-800 border-dashed rounded-xl p-8 text-center">
      <Briefcase className="w-8 h-8 text-gray-600 mx-auto mb-3" />
      <p className="text-sm text-gray-400">
        No applications tracked yet. Log your first application to start gaining intelligence.
      </p>
      <Link
        href="/applications?action=add"
        className="mt-3 inline-flex items-center gap-1 text-sm text-violet-400 hover:text-violet-300"
      >
        Log Application <ArrowRight className="w-3 h-3" />
      </Link>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-pulse">
      <div className="h-8 w-48 bg-gray-800 rounded" />
      <div className="grid grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-24 bg-gray-900 rounded-xl" />
        ))}
      </div>
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 h-64 bg-gray-900 rounded-xl" />
        <div className="h-64 bg-gray-900 rounded-xl" />
      </div>
    </div>
  );
}

function ErrorState({ message, onRetry, retrying }: { message: string; onRetry: () => void; retrying: boolean }) {
  const isNetworkError = message.toLowerCase().includes("not responding") || message.toLowerCase().includes("waking");
  const isAuthError = message.toLowerCase().includes("session expired") || message.toLowerCase().includes("sign out");
  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-center">
        <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
        <p className="text-gray-400 mb-1">{message}</p>
        {isNetworkError && (
          <p className="text-xs text-gray-600 mb-4">The server may be waking up — this can take ~30 seconds.</p>
        )}
        {!isAuthError && (
          <button
            onClick={onRetry}
            disabled={retrying}
            className="px-4 py-2 text-sm bg-violet-600 hover:bg-violet-500 text-white rounded-lg transition-colors disabled:opacity-50 mt-4"
          >
            {retrying ? "Retrying..." : "Retry"}
          </button>
        )}
      </div>
    </div>
  );
}
