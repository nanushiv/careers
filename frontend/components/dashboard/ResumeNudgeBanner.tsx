"use client";

import { useState } from "react";
import { AlertTriangle, X, ArrowRight, CheckCircle2 } from "lucide-react";
import Link from "next/link";

interface ResumeNudgeBannerProps {
  score: number;
  topGaps: string[];
  resumeId: string;
  analysisDate: string;
}

export function ResumeNudgeBanner({ score, topGaps, resumeId, analysisDate }: ResumeNudgeBannerProps) {
  const [dismissed, setDismissed] = useState(false);
  const [marked, setMarked] = useState(false);

  if (dismissed || score >= 75) return null;

  const color = score >= 50
    ? { bg: "bg-amber-950/40 border-amber-500/30", icon: "text-amber-400", badge: "bg-amber-500/20 text-amber-300" }
    : { bg: "bg-red-950/40 border-red-500/30", icon: "text-red-400", badge: "bg-red-500/20 text-red-300" };

  if (marked) {
    return (
      <div className="flex items-center gap-3 p-4 bg-green-950/30 border border-green-500/30 rounded-xl mb-6">
        <CheckCircle2 className="w-5 h-5 text-green-400 shrink-0" />
        <p className="text-sm text-green-300">
          Great! Re-upload your updated resume and run a new analysis to see your improved score.
        </p>
        <Link href="/resume" className="ml-auto flex items-center gap-1 text-xs text-green-400 hover:text-green-300 whitespace-nowrap">
          Upload now <ArrowRight className="w-3 h-3" />
        </Link>
      </div>
    );
  }

  return (
    <div className={`relative p-4 border rounded-xl mb-6 ${color.bg}`}>
      <button onClick={() => setDismissed(true)}
        className="absolute top-3 right-3 text-gray-500 hover:text-gray-300">
        <X className="w-4 h-4" />
      </button>

      <div className="flex items-start gap-3">
        <AlertTriangle className={`w-5 h-5 shrink-0 mt-0.5 ${color.icon}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <p className="text-sm font-semibold text-gray-100">
              Your resume scored {score}/100 — here's what to fix
            </p>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${color.badge}`}>
              Action needed
            </span>
          </div>

          {/* Top 3 gaps */}
          <div className="space-y-1 mb-3">
            {topGaps.slice(0, 3).map((gap, i) => (
              <p key={i} className="text-xs text-gray-300 flex items-start gap-2">
                <span className="text-gray-500 shrink-0">{i + 1}.</span>{gap}
              </p>
            ))}
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <Link href={`/resume/${resumeId}/analysis`}
              className="text-xs text-violet-400 hover:text-violet-300 flex items-center gap-1 font-medium">
              See full analysis <ArrowRight className="w-3 h-3" />
            </Link>
            <span className="text-gray-600 text-xs">·</span>
            <button onClick={() => setMarked(true)}
              className="text-xs text-gray-400 hover:text-gray-200">
              I've updated my resume ✓
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
