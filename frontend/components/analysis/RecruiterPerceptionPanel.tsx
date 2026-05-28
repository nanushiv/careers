"use client";

import { Analysis } from "@/lib/api";
import { Eye, ThumbsUp, ThumbsDown, MessageSquare } from "lucide-react";

const LIKELIHOOD_CONFIG = {
  low: { label: "Unlikely to shortlist", color: "text-red-400", bg: "bg-red-500/10" },
  medium: { label: "May shortlist", color: "text-amber-400", bg: "bg-amber-500/10" },
  high: { label: "Likely to shortlist", color: "text-green-400", bg: "bg-green-500/10" },
  very_high: { label: "Strong candidate", color: "text-emerald-400", bg: "bg-emerald-500/10" },
};

export function RecruiterPerceptionPanel({ analysis }: { analysis: Analysis }) {
  const signals = (analysis as any).recruiter_signals || {};
  const {
    perception_score,
    first_impression,
    likelihood_to_shortlist,
    standout_positives = [],
    immediate_concerns = [],
    positioning_gaps = [],
    narrative_story,
    recommended_changes = [],
  } = signals;

  const likelihood = LIKELIHOOD_CONFIG[likelihood_to_shortlist as keyof typeof LIKELIHOOD_CONFIG] || LIKELIHOOD_CONFIG.medium;

  return (
    <div className="space-y-4">
      {/* Score + first impression */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 text-center">
          <p className="text-5xl font-bold text-violet-400">{Math.round(perception_score ?? 0)}</p>
          <p className="text-xs text-gray-400 mt-1">Recruiter Score</p>
          <div className={`mt-3 inline-flex px-3 py-1 rounded-full text-xs font-medium ${likelihood.bg} ${likelihood.color}`}>
            {likelihood.label}
          </div>
        </div>
        <div className="md:col-span-2 bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p className="text-xs font-semibold text-gray-400 flex items-center gap-2 mb-3">
            <Eye className="w-3.5 h-3.5" /> RECRUITER'S FIRST 30 SECONDS
          </p>
          <p className="text-sm text-gray-200 leading-relaxed italic">"{first_impression}"</p>
          {narrative_story && (
            <div className="mt-3 pt-3 border-t border-gray-800">
              <p className="text-xs text-gray-500 mb-1">How they'll narrate your story:</p>
              <p className="text-xs text-gray-300 italic">"{narrative_story}"</p>
            </div>
          )}
        </div>
      </div>

      {/* Positives + concerns */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p className="text-sm font-semibold text-green-400 mb-3 flex items-center gap-2">
            <ThumbsUp className="w-4 h-4" /> What Stands Out
          </p>
          <div className="space-y-3">
            {standout_positives.map((p: any, i: number) => (
              <div key={i}>
                <p className="text-xs font-medium text-gray-200">{p.point}</p>
                <p className="text-xs text-gray-500 mt-0.5">{p.why_it_matters}</p>
              </div>
            ))}
            {standout_positives.length === 0 && (
              <p className="text-xs text-gray-500">No standout positives identified.</p>
            )}
          </div>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p className="text-sm font-semibold text-red-400 mb-3 flex items-center gap-2">
            <ThumbsDown className="w-4 h-4" /> Immediate Concerns
          </p>
          <div className="space-y-3">
            {immediate_concerns.map((c: any, i: number) => (
              <div key={i} className={`${c.severity === "dealbreaker" ? "text-red-300" : "text-amber-300"}`}>
                <p className="text-xs font-medium">{c.concern}</p>
                <p className="text-xs opacity-70 mt-0.5">{c.context}</p>
              </div>
            ))}
            {immediate_concerns.length === 0 && (
              <p className="text-xs text-gray-500">No major concerns flagged.</p>
            )}
          </div>
        </div>
      </div>

      {/* Recommended changes */}
      {recommended_changes.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <MessageSquare className="w-4 h-4" /> Recommended Resume Changes
          </p>
          <div className="space-y-4">
            {recommended_changes.map((change: any, i: number) => (
              <div key={i} className="text-xs space-y-1">
                <p className="font-medium text-gray-200">{change.change}</p>
                {change.before_example && (
                  <div className="grid grid-cols-2 gap-2 mt-1">
                    <div className="bg-red-950/30 border border-red-500/20 rounded p-2">
                      <p className="text-red-400 font-medium mb-0.5">Before</p>
                      <p className="text-gray-300">{change.before_example}</p>
                    </div>
                    <div className="bg-green-950/30 border border-green-500/20 rounded p-2">
                      <p className="text-green-400 font-medium mb-0.5">After</p>
                      <p className="text-gray-300">{change.after_example}</p>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
