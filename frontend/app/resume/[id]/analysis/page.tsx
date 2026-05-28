"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useParams, useSearchParams } from "next/navigation";
import { Brain, Loader2, CheckCircle2, AlertTriangle, TrendingUp, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { api, Analysis } from "@/lib/api";
import { ATSScoreCard } from "@/components/analysis/ATSScoreCard";
import { RecruiterPerceptionPanel } from "@/components/analysis/RecruiterPerceptionPanel";
import { GapAnalysisGrid } from "@/components/analysis/GapAnalysisGrid";
import { ImprovementRoadmap } from "@/components/analysis/ImprovementRoadmap";

export default function AnalysisResultsPage() {
  const { getToken } = useAuth();
  const params = useParams();
  const searchParams = useSearchParams();
  const resumeId = params.id as string;
  const jobId = searchParams.get("job");

  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [polling, setPolling] = useState(!!jobId);
  const [activeTab, setActiveTab] = useState<"ats" | "recruiter" | "readiness" | "roadmap">("ats");

  // Poll for results when job is running
  useEffect(() => {
    if (!jobId) { loadAnalyses(); return; }

    const interval = setInterval(async () => {
      const token = await getToken();
      if (!token) return;

      // Check job status via analyses list
      const resp = await api.listAnalyses(token, { resume_id: resumeId });
      if (resp.data && resp.data.length > 0) {
        setAnalyses(resp.data);
        setPolling(false);
        setLoading(false);
        clearInterval(interval);
      }
    }, 3000);

    setTimeout(() => { clearInterval(interval); setPolling(false); setLoading(false); }, 120000);
    return () => clearInterval(interval);
  }, [jobId]);

  const loadAnalyses = async () => {
    const token = await getToken();
    if (!token) return;
    const resp = await api.listAnalyses(token, { resume_id: resumeId });
    if (resp.data) setAnalyses(resp.data);
    setLoading(false);
  };

  const getAnalysis = (type: string) => analyses.find(a => a.analysis_type === type);
  const ats = getAnalysis("ats");
  const recruiter = getAnalysis("recruiter");
  const readiness = getAnalysis("readiness");

  const TABS = [
    { id: "ats", label: "ATS Score", icon: CheckCircle2, available: !!ats },
    { id: "recruiter", label: "Recruiter View", icon: Brain, available: !!recruiter },
    { id: "readiness", label: "PM Readiness", icon: TrendingUp, available: !!readiness },
    { id: "roadmap", label: "Roadmap", icon: AlertTriangle, available: !!ats },
  ] as const;

  if (loading || polling) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <Loader2 className="w-10 h-10 text-violet-400 animate-spin" />
        <p className="text-gray-300 font-medium">
          {polling ? "AI is analyzing your resume…" : "Loading results…"}
        </p>
        {polling && (
          <p className="text-sm text-gray-500">Usually takes 20–40 seconds</p>
        )}
      </div>
    );
  }

  if (analyses.length === 0) {
    return (
      <div className="text-center py-20">
        <p className="text-gray-400">No analyses found. Run an analysis from the Resume Vault.</p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-6">
        <Link href="/resume" className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-200 transition-colors mb-3">
          <ArrowLeft className="w-4 h-4" />
          Back to Resume Vault
        </Link>
        <h1 className="text-2xl font-bold text-white">Analysis Results</h1>
        <p className="text-sm text-gray-400 mt-0.5">{analyses.length} analyses completed</p>
      </div>

      {/* Score summary row */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {ats && <ScorePill label="ATS Score" score={ats.overall_score} />}
        {recruiter && <ScorePill label="Recruiter Score" score={recruiter.overall_score} />}
        {readiness && <ScorePill label="PM Readiness" score={readiness.overall_score} />}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-gray-900 border border-gray-800 rounded-xl p-1">
        {TABS.filter(t => t.available).map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all flex-1 justify-center ${
              activeTab === tab.id
                ? "bg-violet-600 text-white"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div>
        {activeTab === "ats" && ats && <ATSScoreCard analysis={ats} />}
        {activeTab === "recruiter" && recruiter && <RecruiterPerceptionPanel analysis={recruiter} />}
        {activeTab === "readiness" && readiness && (
          <ReadinessPanel analysis={readiness} />
        )}
        {activeTab === "roadmap" && ats && <ImprovementRoadmap analysis={ats} />}
      </div>
    </div>
  );
}

function ScorePill({ label, score }: { label: string; score?: number | null }) {
  const s = score ?? 0;
  const color = s >= 75 ? "text-green-400" : s >= 50 ? "text-amber-400" : "text-red-400";
  const bg = s >= 75 ? "bg-green-500/10 border-green-500/20" : s >= 50 ? "bg-amber-500/10 border-amber-500/20" : "bg-red-500/10 border-red-500/20";
  return (
    <div className={`rounded-xl border p-4 text-center ${bg}`}>
      <p className={`text-3xl font-bold ${color}`}>{Math.round(s)}</p>
      <p className="text-xs text-gray-400 mt-1">{label}</p>
    </div>
  );
}

function ReadinessPanel({ analysis }: { analysis: Analysis }) {
  const dims = (analysis as any).readiness_breakdown?.dimensions || {};
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
      <h3 className="font-semibold text-white">PM Readiness Breakdown</h3>
      {Object.entries(dims).map(([dim, data]: [string, any]) => (
        <div key={dim}>
          <div className="flex justify-between mb-1">
            <span className="text-sm text-gray-300 capitalize">{dim.replace(/_/g, " ")}</span>
            <span className="text-sm font-medium text-violet-400">{data?.score ?? 0}/100</span>
          </div>
          <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-violet-500 rounded-full transition-all duration-700"
              style={{ width: `${data?.score ?? 0}%` }}
            />
          </div>
          {data?.gaps?.length > 0 && (
            <p className="text-xs text-gray-500 mt-1">{data.gaps[0]}</p>
          )}
        </div>
      ))}
    </div>
  );
}
