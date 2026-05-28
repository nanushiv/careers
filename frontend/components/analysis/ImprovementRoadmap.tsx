"use client";

import { Analysis } from "@/lib/api";
import { CheckCircle2, Clock, Zap } from "lucide-react";

const EFFORT_CONFIG: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  minutes: { icon: Zap, color: "text-green-400", label: "Quick win" },
  hours:   { icon: Clock, color: "text-amber-400", label: "Few hours" },
  days:    { icon: Clock, color: "text-red-400", label: "Few days" },
};

export function ImprovementRoadmap({ analysis }: { analysis: Analysis }) {
  const improvements = analysis.improvements || [];
  const quickFixes = (analysis as any).quick_fixes || [];

  const allActions = [
    ...improvements.map((imp: any) => ({
      action: imp.action,
      impact: imp.impact,
      effort: imp.effort || "hours",
      source: "gap",
    })),
    ...quickFixes.map((fix: any) => ({
      action: fix.action,
      impact: fix.impact,
      effort: fix.effort || "minutes",
      source: "ai",
    })),
  ];

  if (allActions.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
        <CheckCircle2 className="w-8 h-8 text-green-400 mx-auto mb-3" />
        <p className="text-gray-300">No improvement actions generated yet.</p>
        <p className="text-sm text-gray-500 mt-1">Run a full analysis with a job description for a personalized roadmap.</p>
      </div>
    );
  }

  const sorted = allActions.sort((a, b) => {
    const order = { high: 0, medium: 1, low: 2 };
    return (order[a.impact as keyof typeof order] ?? 2) - (order[b.impact as keyof typeof order] ?? 2);
  });

  return (
    <div className="space-y-4">
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <p className="text-sm font-semibold text-white mb-4">
          Improvement Roadmap — {allActions.length} actions
        </p>
        <div className="space-y-3">
          {sorted.map((item, i) => {
            const effortCfg = EFFORT_CONFIG[item.effort] || EFFORT_CONFIG.hours;
            const Icon = effortCfg.icon;
            const impactColor = item.impact === "high" ? "text-red-400" : item.impact === "medium" ? "text-amber-400" : "text-gray-400";

            return (
              <div key={i} className="flex items-start gap-3 p-3 bg-gray-800/50 rounded-lg">
                <div className="w-6 h-6 rounded-full bg-violet-600/20 border border-violet-500/30 flex items-center justify-center shrink-0 mt-0.5">
                  <span className="text-xs text-violet-400 font-bold">{i + 1}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-200">{item.action}</p>
                  <div className="flex items-center gap-3 mt-1.5">
                    <span className={`text-xs font-medium ${impactColor}`}>
                      {item.impact} impact
                    </span>
                    <span className={`flex items-center gap-1 text-xs ${effortCfg.color}`}>
                      <Icon className="w-3 h-3" />{effortCfg.label}
                    </span>
                    {item.source === "ai" && (
                      <span className="text-xs text-violet-400">AI suggested</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
