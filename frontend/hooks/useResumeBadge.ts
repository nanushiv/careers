"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";

export function useResumeBadge() {
  const { getToken } = useAuth();
  const [showBadge, setShowBadge] = useState(false);

  useEffect(() => {
    const check = async () => {
      try {
        const token = await getToken();
        if (!token) return;

        const [analysesResp, resumesResp] = await Promise.all([
          api.listAnalyses(token, { analysis_type: "ats" }),
          api.listResumes(token),
        ]);

        const latestAnalysis = analysesResp.data?.[0];
        const latestResume = resumesResp.data?.[0];

        if (!latestAnalysis || !latestResume) return;

        const score = latestAnalysis.overall_score ?? 0;
        const analysisDate = new Date(latestAnalysis.created_at);
        const daysSince = (Date.now() - analysisDate.getTime()) / (1000 * 60 * 60 * 24);

        // Show badge if: score < 60 AND no new upload in last 7 days
        const hasRecentUpload = latestResume.created_at > latestAnalysis.created_at;
        setShowBadge(score < 60 && daysSince > 7 && !hasRecentUpload);
      } catch {}
    };
    check();
  }, [getToken]);

  return showBadge;
}
