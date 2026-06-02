"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { motion } from "framer-motion";
import {
  TrendingUp, AlertCircle, CheckCircle2, Clock,
  ArrowRight, Plus, Briefcase, FileText, Brain
} from "lucide-react";
import Link from "next/link";
import { api, DashboardData } from "@/lib/api";
import { CareerHealthGauge } from "@/components/dashboard/CareerHealthGauge";
import { InsightCard } from "@/components/dashboard/InsightCard";
import { PipelineMini } from "@/components/dashboard/PipelineMini";
import { ApplicationCard } from "@/components/applications/ApplicationCard";
import { StageDistribution } from "@/components/dashboard/StageDistribution";
import { ResumeNudgeBanner } from "@/components/dashboard/ResumeNudgeBanner";

const STAGES = ["applied", "screening", "phone_screen", "technical", "case_study", "final", "offer"];

export default function DashboardPage() {
  const { getToken } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [latestAnalysis, setLatestAnalysis] = useState<any>(null);
  const [insights, setInsights] = useState<any[]>([]);
  const [generatingInsights, setGeneratingInsights] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const token = await getToken();
        if (!token) return;
        const [resp, analysisResp] = await Promise.all([
        api.getDashboard(token),
        api.listAnalyses(token, { analysis_type: "ats" }),
      ]);
        if (analysisResp.data?.[0]) setLatestAnalysis(analysisResp.data[0]);
        if (resp.data) {
          setData(resp.data);
          setInsights(resp.data.insights ?? []);
        }
      } catch (e) {
        setError("Failed to load dashboard");
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [getToken]);

  if (loading) return <DashboardSkeleton />;
  if (error || !data) return <ErrorState message={error || "No data"} />;

  const { career_health_score, pipeline_summary, follow_ups, resumes, recent_applications } = data;

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
        const resp = await api.listInsights(token);
        if (resp.data && resp.data.length > 0) {
          setInsights(resp.data);
          setGeneratingInsights(false);
          clearInterval(poll);
        }
        if (attempts >= 10) {
          setGeneratingInsights(false);
          clearInterval(poll);
        }
      }, 3000);
    } catch {
      setGeneratingInsights(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {latestAnalysis && (
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
        <div className="lg:col-span-1 bg-gray-900 border border-gray-800 rounded-xl p-6 flex flex-col items-center">
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
            <EmptyInsights hasAnalysis={!!latestAnalysis} onGenerate={handleGenerateInsights} generating={generatingInsights} />
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
                    {fu.applications?.company_name} — {fu.due_date}
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

function EmptyInsights({ hasAnalysis, onGenerate, generating }: { hasAnalysis: boolean; onGenerate: () => void; generating: boolean }) {
  return (
    <div className="bg-gray-900 border border-gray-800 border-dashed rounded-xl p-8 text-center">
      <Brain className={`w-8 h-8 mx-auto mb-3 ${generating ? "text-violet-500 animate-pulse" : "text-gray-600"}`} />
      {hasAnalysis ? (
        <>
          <p className="text-sm text-gray-400">
            {generating ? "Generating your AI insights..." : "No insights yet — generate them now based on your applications."}
          </p>
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

function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-center">
        <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
        <p className="text-gray-400">{message}</p>
      </div>
    </div>
  );
}
