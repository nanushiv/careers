"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Brain, TrendingUp, Zap, Lock, RefreshCw } from "lucide-react";
import { api, Insight, Analysis } from "@/lib/api";
import { InsightCard } from "@/components/dashboard/InsightCard";
import { RecruiterPerceptionPanel } from "@/components/analysis/RecruiterPerceptionPanel";

export default function IntelligencePage() {
  const { getToken } = useAuth();
  const [insights, setInsights] = useState<Insight[]>([]);
  const [recruiterAnalysis, setRecruiterAnalysis] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"insights" | "recruiter">("insights");

  useEffect(() => {
    const load = async () => {
      const token = await getToken();
      if (!token) return;
      const [insightsResp, recruiterResp] = await Promise.all([
        api.listInsights(token),
        api.listAnalyses(token, { analysis_type: "recruiter" }),
      ]);
      if (insightsResp.data) setInsights(insightsResp.data);
      if (recruiterResp.data?.[0]) setRecruiterAnalysis(recruiterResp.data[0]);
      setLoading(false);
    };
    load();
  }, [getToken]);

  const handleDismiss = async (id: string) => {
    const token = await getToken();
    if (!token) return;
    await api.dismissInsight(token, id);
    setInsights(prev => prev.filter(i => i.id !== id));
  };

  const critical = insights.filter(i => i.priority === "critical");
  const high = insights.filter(i => i.priority === "high");
  const rest = insights.filter(i => !["critical", "high"].includes(i.priority));

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Brain className="w-6 h-6 text-violet-400" /> AI Intelligence
          </h1>
          <p className="text-sm text-gray-400 mt-0.5">Strategic insights and recruiter perception analysis</p>
        </div>
        <button onClick={() => window.location.reload()}
          className="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-gray-200 bg-gray-800 rounded-lg border border-gray-700 transition-colors">
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-gray-900 border border-gray-800 rounded-xl p-1">
        {[
          { id: "insights", label: "Strategic Insights", icon: Zap },
          { id: "recruiter", label: "Recruiter Perception", icon: TrendingUp },
        ].map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id as any)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all flex-1 justify-center ${
              activeTab === tab.id ? "bg-violet-600 text-white" : "text-gray-400 hover:text-gray-200"
            }`}>
            <tab.icon className="w-4 h-4" />{tab.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => <div key={i} className="h-24 bg-gray-900 rounded-xl animate-pulse" />)}
        </div>
      ) : activeTab === "insights" ? (
        <div className="space-y-6">
          {insights.length === 0 ? (
            <EmptyInsights />
          ) : (
            <>
              {critical.length > 0 && (
                <section>
                  <p className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-3">🔴 Critical</p>
                  <div className="space-y-3">
                    {critical.map(i => <InsightCard key={i.id} insight={i} onDismiss={handleDismiss} />)}
                  </div>
                </section>
              )}
              {high.length > 0 && (
                <section>
                  <p className="text-xs font-semibold text-amber-400 uppercase tracking-wider mb-3">🟡 High Priority</p>
                  <div className="space-y-3">
                    {high.map(i => <InsightCard key={i.id} insight={i} onDismiss={handleDismiss} />)}
                  </div>
                </section>
              )}
              {rest.length > 0 && (
                <section>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Other Insights</p>
                  <div className="space-y-3">
                    {rest.map(i => <InsightCard key={i.id} insight={i} onDismiss={handleDismiss} />)}
                  </div>
                </section>
              )}
            </>
          )}
        </div>
      ) : (
        /* Recruiter tab */
        recruiterAnalysis ? (
          <RecruiterPerceptionPanel analysis={recruiterAnalysis} />
        ) : (
          <EmptyRecruiter />
        )
      )}
    </div>
  );
}

function EmptyInsights() {
  return (
    <div className="text-center py-16 bg-gray-900 border border-gray-800 border-dashed rounded-2xl">
      <Brain className="w-10 h-10 text-gray-600 mx-auto mb-3" />
      <p className="text-gray-400 font-medium">No insights yet</p>
      <p className="text-sm text-gray-500 mt-1">
        Upload a resume and log 5+ applications to unlock AI-powered strategic insights.
      </p>
    </div>
  );
}

function EmptyRecruiter() {
  return (
    <div className="text-center py-16 bg-gray-900 border border-gray-800 border-dashed rounded-2xl">
      <Lock className="w-10 h-10 text-gray-600 mx-auto mb-3" />
      <p className="text-gray-400 font-medium">No recruiter analysis yet</p>
      <p className="text-sm text-gray-500 mt-1">
        Run an analysis from Resume Vault and include "Recruiter Perception" to see how recruiters view your profile.
      </p>
    </div>
  );
}
