"use client";

import { Analysis } from "@/lib/api";
import { CheckCircle2, XCircle, AlertTriangle } from "lucide-react";

export function ATSScoreCard({ analysis }: { analysis: Analysis }) {
  const { keyword_analysis, gaps, improvements, ats_red_flags } = analysis;
  const score = analysis.overall_score ?? 0;
  const scoreColor = score >= 75 ? "#22c55e" : score >= 50 ? "#f59e0b" : "#ef4444";

  return (
    <div className="space-y-4">
      {/* Score + breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="md:col-span-1 bg-gray-900 border border-gray-800 rounded-xl p-6 flex flex-col items-center justify-center">
          <div className="text-5xl font-bold" style={{ color: scoreColor }}>
            {Math.round(score)}
          </div>
          <div className="text-xs text-gray-400 mt-1">ATS Score</div>
        </div>
        <div className="md:col-span-3 grid grid-cols-3 gap-3">
          {[
            { label: "Keywords", score: analysis.keyword_score },
            { label: "Format", score: analysis.format_score },
            { label: "Experience", score: analysis.experience_score },
          ].map(({ label, score: s }) => (
            <div key={label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className="text-xs text-gray-400 mb-2">{label}</p>
              <p className="text-2xl font-bold text-white">{Math.round(s ?? 0)}</p>
              <div className="w-full h-1.5 bg-gray-800 rounded-full mt-2 overflow-hidden">
                <div
                  className="h-full rounded-full bg-violet-500"
                  style={{ width: `${s ?? 0}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Red flags */}
      {(ats_red_flags as any[])?.length > 0 && (
        <div className="bg-red-950/30 border border-red-500/30 rounded-xl p-4">
          <p className="text-sm font-semibold text-red-300 mb-2 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" /> ATS Red Flags
          </p>
          {(ats_red_flags as string[]).map((flag, i) => (
            <p key={i} className="text-xs text-red-400 mt-1">• {flag}</p>
          ))}
        </div>
      )}

      {/* Keywords */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p className="text-sm font-semibold text-green-400 mb-3 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" /> Keywords Found ({keyword_analysis?.required_found?.length ?? 0})
          </p>
          <div className="flex flex-wrap gap-2">
            {(keyword_analysis?.required_found ?? []).map((kw: string) => (
              <span key={kw} className="text-xs px-2 py-1 bg-green-500/10 text-green-300 rounded-full border border-green-500/20">
                {kw}
              </span>
            ))}
          </div>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p className="text-sm font-semibold text-red-400 mb-3 flex items-center gap-2">
            <XCircle className="w-4 h-4" /> Keywords Missing ({keyword_analysis?.required_missing?.length ?? 0})
          </p>
          <div className="flex flex-wrap gap-2">
            {(keyword_analysis?.required_missing ?? []).map((kw: string) => (
              <span key={kw} className="text-xs px-2 py-1 bg-red-500/10 text-red-300 rounded-full border border-red-500/20">
                {kw}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Gaps */}
      {gaps?.length > 0 && <GapAnalysisGrid gaps={gaps} />}
    </div>
  );
}

function GapAnalysisGrid({ gaps }: { gaps: any[] }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <p className="text-sm font-semibold text-white mb-3">Gaps to Fix</p>
      <div className="space-y-3">
        {gaps.slice(0, 6).map((gap, i) => {
          const severityColor = {
            critical: "border-l-red-500 bg-red-950/20",
            high: "border-l-amber-500 bg-amber-950/20",
            medium: "border-l-blue-500 bg-blue-950/20",
            low: "border-l-gray-500 bg-gray-800/40",
          }[gap.severity as string] || "border-l-gray-500 bg-gray-800/40";

          return (
            <div key={i} className={`border-l-2 pl-3 py-2 rounded-r-lg ${severityColor}`}>
              <p className="text-xs font-medium text-gray-200">{gap.description}</p>
              {gap.fix && <p className="text-xs text-gray-400 mt-0.5">Fix: {gap.fix}</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
