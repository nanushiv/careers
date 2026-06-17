"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useParams, useSearchParams } from "next/navigation";
import { Brain, Loader2, CheckCircle2, AlertTriangle, TrendingUp, ArrowLeft, Sparkles, Download, Lock, Target } from "lucide-react";
import Link from "next/link";
import { api, Analysis } from "@/lib/api";
import { ATSScoreCard } from "@/components/analysis/ATSScoreCard";
import { RecruiterPerceptionPanel } from "@/components/analysis/RecruiterPerceptionPanel";
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
  const [activeTab, setActiveTab] = useState<"ats" | "recruiter" | "readiness" | "role_fit" | "roadmap">("ats");
  const [userPlan, setUserPlan] = useState<string>("free");
  const [pollingError, setPollingError] = useState<string | null>(null);
  const [rewriteStatus, setRewriteStatus] = useState<"idle" | "loading" | "polling" | "completed" | "failed">("idle");
  const [improvedResumeUrl, setImprovedResumeUrl] = useState<string | null>(null);
  const [improvedPdfUrl, setImprovedPdfUrl] = useState<string | null>(null);
  const [projectedAtsScore, setProjectedAtsScore] = useState<number | null>(null);

  const downloadFile = async (url: string, filename: string) => {
    const res = await fetch(url);
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  useEffect(() => {
    (async () => {
      const token = await getToken();
      if (!token) return;
      const resp = await api.getMe(token);
      if (resp.data) setUserPlan(resp.data.plan);
    })();
  }, []);

  useEffect(() => {
    if (!jobId) { loadAnalyses(); return; }

    const interval = setInterval(async () => {
      try {
        const token = await getToken();
        if (!token) { clearInterval(interval); setPolling(false); setLoading(false); return; }
        const resp = await api.listAnalyses(token, { resume_id: resumeId });
        if (resp.error) { clearInterval(interval); setPolling(false); setLoading(false); setPollingError("Failed to load analysis results."); return; }
        const real = (resp.data || []).filter(a => a.analysis_type !== "rewrite");
        if (real.length > 0) {
          setAnalyses(resp.data || []);
          checkRewriteRecord(resp.data || []);
          setPolling(false);
          setLoading(false);
          clearInterval(interval);
        }
      } catch {
        clearInterval(interval);
        setPolling(false);
        setLoading(false);
        setPollingError("Connection error. Please refresh.");
      }
    }, 3000);

    setTimeout(() => { clearInterval(interval); setPolling(false); setLoading(false); setPollingError("Analysis is taking longer than expected. Please refresh."); }, 120000);
    return () => clearInterval(interval);
  }, [jobId]);

  const loadAnalyses = async () => {
    const token = await getToken();
    if (!token) return;
    const resp = await api.listAnalyses(token, { resume_id: resumeId });
    if (resp.data) {
      setAnalyses(resp.data);
      checkRewriteRecord(resp.data);
    }
    setLoading(false);
  };

  const isValidFileUrl = (url?: string) =>
    !!url && !url.startsWith("https://files.careeros.ai");

  const checkRewriteRecord = (data: Analysis[]) => {
    const rewrite = data.find(a => a.analysis_type === "rewrite");
    if (!rewrite) return;
    if (rewrite.rewrite_status === "completed" && isValidFileUrl(rewrite.improved_resume_url)) {
      setImprovedResumeUrl(rewrite.improved_resume_url!);
      if (isValidFileUrl(rewrite.improved_pdf_url)) setImprovedPdfUrl(rewrite.improved_pdf_url!);
      if (rewrite.overall_score && rewrite.overall_score > 0) setProjectedAtsScore(rewrite.overall_score);
      setRewriteStatus("completed");
    } else if (rewrite.rewrite_status === "processing") {
      setRewriteStatus("polling");
      startRewritePolling();
    }
  };

  const handleDownloadImproved = async () => {
    if (userPlan === "free") { window.location.href = "/pricing"; return; }
    setRewriteStatus("loading");
    try {
      const token = await getToken();
      if (!token) return;
      await api.triggerRewrite(token, resumeId);
      setRewriteStatus("polling");
      startRewritePolling();
    } catch {
      setRewriteStatus("failed");
    }
  };

  const startRewritePolling = () => {
    const interval = setInterval(async () => {
      const token = await getToken();
      if (!token) return;
      const resp = await api.listAnalyses(token, { resume_id: resumeId });
      const rewrite = (resp.data || []).find(a => a.analysis_type === "rewrite");
      if (rewrite?.rewrite_status === "completed" && isValidFileUrl(rewrite.improved_resume_url)) {
        setImprovedResumeUrl(rewrite.improved_resume_url!);
        if (isValidFileUrl(rewrite.improved_pdf_url)) setImprovedPdfUrl(rewrite.improved_pdf_url!);
        if (rewrite.overall_score && rewrite.overall_score > 0) setProjectedAtsScore(rewrite.overall_score);
        setRewriteStatus("completed");
        clearInterval(interval);
      } else if (rewrite?.rewrite_status === "failed") {
        setRewriteStatus("failed");
        clearInterval(interval);
      }
    }, 4000);
    setTimeout(() => clearInterval(interval), 120000);
  };

  const getAnalysis = (type: string) => analyses.find(a => a.analysis_type === type);
  const ats = getAnalysis("ats");
  const recruiter = getAnalysis("recruiter");
  const readiness = getAnalysis("readiness");
  const roleFit = getAnalysis("role_fit");

  // Only count real analyses (exclude rewrite metadata records)
  const realCount = analyses.filter(a => a.analysis_type !== "rewrite").length;

  const TABS = [
    { id: "ats" as const, label: "ATS Score", icon: CheckCircle2, available: !!ats },
    { id: "recruiter" as const, label: "Recruiter View", icon: Brain, available: !!recruiter },
    { id: "readiness" as const, label: "PM Readiness", icon: TrendingUp, available: !!readiness },
    { id: "role_fit" as const, label: "Role Fit", icon: Target, available: !!roleFit },
    { id: "roadmap" as const, label: "Roadmap", icon: AlertTriangle, available: !!ats },
  ];

  if (pollingError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <AlertTriangle className="w-10 h-10 text-amber-400" />
        <p className="text-gray-300 font-medium">{pollingError}</p>
        <button onClick={() => { setPollingError(null); setLoading(true); loadAnalyses(); }} className="text-sm text-violet-400 hover:text-violet-300 underline">Try again</button>
      </div>
    );
  }

  if (loading || polling) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <Loader2 className="w-10 h-10 text-violet-400 animate-spin" />
        <p className="text-gray-300 font-medium">
          {polling ? "AI is analyzing your resume…" : "Loading results…"}
        </p>
        {polling && <p className="text-sm text-gray-500">Usually takes 20–40 seconds</p>}
      </div>
    );
  }

  if (realCount === 0) {
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
        <p className="text-sm text-gray-400 mt-0.5">{realCount} analyses completed</p>
      </div>

      {/* Score summary row */}
      <div className={`grid gap-4 mb-6 ${roleFit ? "grid-cols-4" : "grid-cols-3"}`}>
        {ats && <ScorePill label="ATS Score" score={ats.overall_score} />}
        {recruiter && <ScorePill label="Recruiter Score" score={recruiter.overall_score} />}
        {readiness && <ScorePill label="PM Readiness" score={readiness.overall_score} />}
        {roleFit && <ScorePill label="Role Fit" score={roleFit.overall_score} />}
      </div>

      {/* Auto-Fix Resume Banner */}
      <div className="mb-6 bg-gradient-to-r from-violet-950/40 to-violet-900/20 border border-violet-500/30 rounded-xl p-4 flex items-center justify-between gap-4">
        <div>
          <p className="font-semibold text-white text-sm flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-violet-400" />
            AI-Improved Resume
          </p>
          <p className="text-xs text-gray-400 mt-0.5">
            {rewriteStatus === "completed" && projectedAtsScore
              ? `All gaps fixed — projected ATS score: ${projectedAtsScore}% (up from ${ats?.overall_score ?? "?"}%)`
              : "Download a DOCX with all gaps fixed, every missing keyword added, and bullets strengthened."}
          </p>
        </div>
        {rewriteStatus === "completed" && improvedResumeUrl ? (
          <div className="flex items-center gap-2 shrink-0">
            <button onClick={() => downloadFile(improvedResumeUrl!, "improved-resume.docx")}
              className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium rounded-xl transition-colors">
              <Download className="w-4 h-4" /> DOCX
            </button>
            {improvedPdfUrl && (
              <button onClick={() => downloadFile(improvedPdfUrl, "improved-resume.pdf")}
                className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium rounded-xl transition-colors">
                <Download className="w-4 h-4" /> PDF
              </button>
            )}
          </div>
        ) : rewriteStatus === "polling" || rewriteStatus === "loading" ? (
          <button disabled className="flex items-center gap-2 px-4 py-2 bg-violet-600/50 text-white text-sm font-medium rounded-xl shrink-0 cursor-not-allowed">
            <Loader2 className="w-4 h-4 animate-spin" />
            {rewriteStatus === "loading" ? "Starting…" : "Rewriting… (~30s)"}
          </button>
        ) : rewriteStatus === "failed" ? (
          <button onClick={handleDownloadImproved}
            className="flex items-center gap-2 px-4 py-2 bg-red-600/30 hover:bg-red-600/50 text-red-300 text-sm font-medium rounded-xl border border-red-500/30 transition-colors shrink-0">
            Failed — try again
          </button>
        ) : userPlan !== "free" ? (
          <button onClick={handleDownloadImproved}
            className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium rounded-xl transition-colors shrink-0">
            <Sparkles className="w-4 h-4" /> Generate Improved Resume
          </button>
        ) : (
          <Link href="/pricing"
            className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-violet-300 text-sm font-medium rounded-xl border border-violet-500/30 transition-colors shrink-0">
            <Lock className="w-4 h-4" /> Pro Only — Upgrade
          </Link>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-gray-900 border border-gray-800 rounded-xl p-1">
        {TABS.filter(t => t.available).map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all flex-1 justify-center ${
              activeTab === tab.id ? "bg-violet-600 text-white" : "text-gray-400 hover:text-gray-200"
            }`}>
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div>
        {activeTab === "ats" && ats && <ATSScoreCard analysis={ats} />}
        {activeTab === "recruiter" && recruiter && <RecruiterPerceptionPanel analysis={recruiter} />}
        {activeTab === "readiness" && readiness && <ReadinessPanel analysis={readiness} />}
        {activeTab === "role_fit" && roleFit && <RoleFitPanel analysis={roleFit} />}
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
  const data = (analysis as any).readiness_breakdown || {};
  const dims = data.dimensions || {};

  if (Object.keys(dims).length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-10 text-center">
        <AlertTriangle className="w-8 h-8 text-amber-400 mx-auto mb-3" />
        <p className="text-gray-300 font-medium">Readiness data unavailable</p>
        <p className="text-sm text-gray-500 mt-1">The AI analysis didn't return dimension data. Re-run the analysis from the Resume Vault.</p>
        <Link href="/resume" className="inline-block mt-4 text-sm text-violet-400 hover:text-violet-300 underline">Go to Resume Vault →</Link>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        {data.positioning_narrative && (
          <p className="text-sm text-gray-300 italic mb-4 pb-4 border-b border-gray-800">"{data.positioning_narrative}"</p>
        )}
        <h3 className="font-semibold text-white mb-4">Readiness Dimensions</h3>
        <div className="space-y-4">
          {Object.entries(dims).map(([dim, d]: [string, any]) => (
            <div key={dim}>
              <div className="flex justify-between mb-1">
                <span className="text-sm text-gray-300 capitalize">{dim.replace(/_/g, " ")}</span>
                <span className="text-sm font-medium text-violet-400">{d?.score ?? 0}/100</span>
              </div>
              <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
                <div className="h-full bg-violet-500 rounded-full transition-all duration-700" style={{ width: `${d?.score ?? 0}%` }} />
              </div>
              {d?.gaps?.length > 0 && <p className="text-xs text-gray-500 mt-1">{d.gaps[0]}</p>}
            </div>
          ))}
        </div>
      </div>
      {data.quick_wins_30_days?.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p className="text-sm font-semibold text-green-400 mb-3">Quick Wins (30 days)</p>
          <ul className="space-y-2">
            {data.quick_wins_30_days.map((w: string, i: number) => (
              <li key={i} className="text-xs text-gray-300 flex gap-2"><span className="text-green-500 shrink-0">✓</span>{w}</li>
            ))}
          </ul>
        </div>
      )}
      {data.critical_missing_experiences?.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p className="text-sm font-semibold text-red-400 mb-3">Critical Missing Experiences</p>
          <ul className="space-y-2">
            {data.critical_missing_experiences.map((e: string, i: number) => (
              <li key={i} className="text-xs text-gray-300 flex gap-2"><span className="text-red-500 shrink-0">✗</span>{e}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function RoleFitPanel({ analysis }: { analysis: Analysis }) {
  const data = (analysis as any).role_fit_analysis || {};
  const dims = data.dimension_scores || {};

  const recColor: Record<string, string> = {
    apply_strong: "text-green-400",
    apply_with_improvements: "text-amber-400",
    stretch_role: "text-orange-400",
    not_recommended: "text-red-400",
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p className="text-5xl font-bold text-violet-400 text-center">{Math.round(data.role_fit_score ?? 0)}</p>
          <p className="text-xs text-gray-400 text-center mt-1">Role Fit Score</p>
          {data.application_recommendation && (
            <p className={`text-center text-xs font-semibold mt-2 ${recColor[data.application_recommendation] || "text-gray-400"}`}>
              {data.application_recommendation.replace(/_/g, " ").toUpperCase()}
            </p>
          )}
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p className="text-xs font-semibold text-gray-400 mb-2">Semantic Match</p>
          <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden mb-3">
            <div className="h-full bg-violet-500 rounded-full" style={{ width: `${data.semantic_score ?? 0}%` }} />
          </div>
          <p className="text-xs text-gray-300">{data.fit_rationale}</p>
        </div>
      </div>

      {Object.keys(dims).length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p className="text-sm font-semibold text-white mb-4">Dimension Scores</p>
          <div className="space-y-3">
            {Object.entries(dims).map(([dim, score]: [string, any]) => (
              <div key={dim}>
                <div className="flex justify-between mb-1">
                  <span className="text-xs text-gray-300 capitalize">{dim.replace(/_/g, " ")}</span>
                  <span className="text-xs font-medium text-violet-400">{score}/100</span>
                </div>
                <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div className="h-full bg-violet-500 rounded-full" style={{ width: `${score}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.positioning_advice && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <p className="text-xs font-semibold text-gray-400 mb-1">Positioning Advice</p>
          <p className="text-sm text-gray-300">{data.positioning_advice}</p>
        </div>
      )}

      {data.critical_gaps?.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p className="text-sm font-semibold text-red-400 mb-3">Critical Gaps</p>
          <div className="space-y-2">
            {data.critical_gaps.map((g: any, i: number) => (
              <div key={i} className="text-xs">
                <span className="text-gray-200">{g.gap}</span>
                {g.bridgeable && <span className="ml-2 text-green-500">(bridgeable)</span>}
                {g.bridge_path && <p className="text-gray-500 mt-0.5">→ {g.bridge_path}</p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
