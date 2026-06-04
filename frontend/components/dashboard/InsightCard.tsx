"use client";

import { useState } from "react";
import Link from "next/link";
import { X, ArrowRight, AlertTriangle, TrendingUp, Info, AlertCircle } from "lucide-react";
import { Insight } from "@/lib/api";

const TYPE_TO_HREF: Record<string, string> = {
  callback_pattern: "/applications",
  positioning_gap: "/resume",
  strategic_pivot: "/jobs",
  momentum: "/applications",
  burnout_signal: "/analytics",
  ats_gap: "/resume",
  keyword_gap: "/resume",
  follow_up_needed: "/applications",
  role_fit: "/jobs",
};

const PRIORITY_CONFIG = {
  critical: {
    icon: AlertCircle,
    bg: "bg-red-950/40",
    border: "border-red-500/30",
    badge: "bg-red-500/20 text-red-300",
    iconColor: "text-red-400",
  },
  high: {
    icon: AlertTriangle,
    bg: "bg-amber-950/30",
    border: "border-amber-500/30",
    badge: "bg-amber-500/20 text-amber-300",
    iconColor: "text-amber-400",
  },
  medium: {
    icon: TrendingUp,
    bg: "bg-blue-950/20",
    border: "border-blue-500/20",
    badge: "bg-blue-500/20 text-blue-300",
    iconColor: "text-blue-400",
  },
  low: {
    icon: Info,
    bg: "bg-gray-900",
    border: "border-gray-800",
    badge: "bg-gray-700 text-gray-300",
    iconColor: "text-gray-400",
  },
};

interface InsightCardProps {
  insight: Insight;
  onDismiss?: (id: string) => void;
}

export function InsightCard({ insight, onDismiss }: InsightCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  const config = PRIORITY_CONFIG[insight.priority] || PRIORITY_CONFIG.medium;
  const Icon = config.icon;

  const handleDismiss = (e: React.MouseEvent) => {
    e.stopPropagation();
    setDismissed(true);
    onDismiss?.(insight.id);
  };

  return (
    <div
      className={`relative rounded-xl border p-4 cursor-pointer transition-all ${config.bg} ${config.border} hover:brightness-110`}
      onClick={() => setExpanded(!expanded)}
    >
      {/* Dismiss button */}
      <button
        onClick={handleDismiss}
        className="absolute top-3 right-3 p-1 rounded text-gray-600 hover:text-gray-400 transition-colors"
      >
        <X className="w-3.5 h-3.5" />
      </button>

      <div className="flex items-start gap-3 pr-6">
        <div className={`p-1.5 rounded-lg ${config.bg} border ${config.border} shrink-0 mt-0.5`}>
          <Icon className={`w-4 h-4 ${config.iconColor}`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${config.badge}`}>
              {insight.priority.charAt(0).toUpperCase() + insight.priority.slice(1)}
            </span>
            <span className="text-xs text-gray-500 capitalize">
              {insight.insight_type.replace(/_/g, " ")}
            </span>
          </div>
          <p className="text-sm font-semibold text-gray-100">{insight.title}</p>
          <p className="text-xs text-gray-400 mt-0.5 leading-relaxed">{insight.summary}</p>

          {expanded && insight.detail && (
            <div className="mt-3 pt-3 border-t border-white/10">
              <p className="text-xs text-gray-300 leading-relaxed">{insight.detail}</p>
              {insight.action && (
                <div className="mt-2">
                  {TYPE_TO_HREF[insight.insight_type] ? (
                    <Link
                      href={TYPE_TO_HREF[insight.insight_type]}
                      onClick={e => e.stopPropagation()}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-violet-600/20 hover:bg-violet-600/40 border border-violet-500/30 rounded-lg text-xs text-violet-300 font-medium transition-colors"
                    >
                      <ArrowRight className="w-3 h-3" />
                      {insight.action}
                    </Link>
                  ) : (
                    <div className="flex items-start gap-2">
                      <ArrowRight className="w-3.5 h-3.5 text-violet-400 shrink-0 mt-0.5" />
                      <p className="text-xs text-violet-300 font-medium">{insight.action}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
