"use client";

import { Gap } from "@/lib/api";

const SEVERITY_STYLE: Record<string, { badge: string; border: string }> = {
  critical: { badge: "bg-red-500/20 text-red-300", border: "border-l-red-500" },
  high:     { badge: "bg-amber-500/20 text-amber-300", border: "border-l-amber-500" },
  medium:   { badge: "bg-blue-500/20 text-blue-300", border: "border-l-blue-500" },
  low:      { badge: "bg-gray-700 text-gray-400", border: "border-l-gray-600" },
};

export function GapAnalysisGrid({ gaps }: { gaps: Gap[] }) {
  if (!gaps?.length) return null;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <p className="text-sm font-semibold text-white mb-4">Gap Analysis ({gaps.length} gaps found)</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {gaps.map((gap, i) => {
          const style = SEVERITY_STYLE[gap.severity] || SEVERITY_STYLE.medium;
          return (
            <div key={i} className={`border-l-2 pl-3 py-2 bg-gray-800/40 rounded-r-lg ${style.border}`}>
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${style.badge}`}>
                  {gap.severity}
                </span>
                {gap.keyword && (
                  <span className="text-xs text-gray-500 font-mono">"{gap.keyword}"</span>
                )}
              </div>
              <p className="text-xs text-gray-200">{gap.description}</p>
              {gap.fix && (
                <p className="text-xs text-violet-400 mt-1">→ {gap.fix}</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
