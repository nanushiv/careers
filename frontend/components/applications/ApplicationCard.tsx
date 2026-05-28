"use client";

import { Building2, Calendar, Star } from "lucide-react";
import { Application } from "@/lib/api";
import { formatDistanceToNow } from "date-fns";

const STAGE_CONFIG: Record<string, { label: string; color: string }> = {
  applied: { label: "Applied", color: "bg-gray-700 text-gray-300" },
  screening: { label: "Screening", color: "bg-blue-500/20 text-blue-300" },
  phone_screen: { label: "Phone Screen", color: "bg-cyan-500/20 text-cyan-300" },
  technical: { label: "Technical", color: "bg-violet-500/20 text-violet-300" },
  case_study: { label: "Case Study", color: "bg-purple-500/20 text-purple-300" },
  final: { label: "Final Round", color: "bg-amber-500/20 text-amber-300" },
  offer: { label: "🎉 Offer", color: "bg-green-500/20 text-green-300" },
  rejected: { label: "Rejected", color: "bg-red-500/20 text-red-300" },
  ghosted: { label: "Ghosted", color: "bg-gray-700/50 text-gray-500" },
  withdrawn: { label: "Withdrawn", color: "bg-gray-800 text-gray-500" },
};

const SOURCE_LABELS: Record<string, string> = {
  linkedin: "LinkedIn",
  company_site: "Company Site",
  referral: "Referral 🤝",
  cold_apply: "Cold Apply",
  job_board: "Job Board",
  recruiter_reach: "Recruiter Outreach",
  unknown: "Unknown",
};

interface ApplicationCardProps {
  application: Application;
  compact?: boolean;
  onClick?: () => void;
}

export function ApplicationCard({ application, compact = false, onClick }: ApplicationCardProps) {
  const stage = STAGE_CONFIG[application.stage] || STAGE_CONFIG.applied;

  const appliedDate = application.applied_date
    ? formatDistanceToNow(new Date(application.applied_date), { addSuffix: true })
    : "Recently";

  return (
    <div
      className="bg-gray-900 border border-gray-800 rounded-xl p-4 hover:border-gray-700 hover:bg-gray-850 transition-all cursor-pointer group"
      onClick={onClick}
    >
        {/* Header */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-gray-700 to-gray-800 flex items-center justify-center shrink-0 border border-gray-700">
              <Building2 className="w-4 h-4 text-gray-400" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-gray-100 truncate flex items-center gap-1">
                {application.company_name}
                {application.is_dream_role && <Star className="w-3 h-3 text-amber-400 fill-amber-400" />}
              </p>
              <p className="text-xs text-gray-400 truncate">{application.role_title}</p>
            </div>
          </div>
        </div>

        {/* Stage badge */}
        <div className="flex items-center justify-between">
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${stage.color}`}>
            {stage.label}
          </span>

          {!compact && application.role_fit_score && (
            <span className="text-xs text-gray-400">
              Fit: <span className="text-violet-400 font-medium">{application.role_fit_score}%</span>
            </span>
          )}
        </div>

        {/* Meta */}
        {!compact && (
          <div className="flex items-center gap-3 mt-3 pt-3 border-t border-gray-800">
            <span className="flex items-center gap-1 text-xs text-gray-500">
              <Calendar className="w-3 h-3" />
              {appliedDate}
            </span>
            {application.application_source && (
              <span className="text-xs text-gray-600">
                {SOURCE_LABELS[application.application_source] || application.application_source}
              </span>
            )}
            {application.has_referral && (
              <span className="text-xs text-emerald-500">Referred</span>
            )}
          </div>
        )}

        {compact && (
          <p className="text-xs text-gray-600 mt-2">{appliedDate}</p>
        )}
    </div>
  );
}
