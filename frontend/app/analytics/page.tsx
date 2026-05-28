"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell, Legend
} from "recharts";
import { api } from "@/lib/api";
import { TrendingUp, BarChart3 } from "lucide-react";

const PIE_COLORS = ["#7c3aed", "#3b82f6", "#06b6d4", "#10b981", "#f59e0b", "#ef4444"];

export default function AnalyticsPage() {
  const { getToken } = useAuth();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      const token = await getToken();
      if (!token) return;
      const resp = await api.getAnalyticsDashboard(token);
      if (resp.data) setData(resp.data);
      setLoading(false);
    };
    load();
  }, [getToken]);

  if (loading) return <Skeleton />;
  if (!data) return <div className="text-gray-400 text-center py-20">No data yet. Start tracking applications.</div>;

  const weeklyData = (data.weekly_snapshots || []).map((s: any) => ({
    week: s.week_start?.slice(5),
    apps: s.apps_submitted || 0,
    callbacks: s.screenings_received || 0,
  }));

  const sourceData = Object.entries(data.source_breakdown || {}).map(([src, stats]: [string, any]) => ({
    name: src.replace(/_/g, " "),
    applications: stats.total,
    callbacks: stats.callbacks,
    rate: stats.callback_rate,
  }));

  const categoryData = Object.entries(data.category_breakdown || {}).map(([cat, count]) => ({
    name: cat,
    value: count as number,
  }));

  const funnelData = (data.stage_drop_off || []).map((s: any) => ({
    stage: s.stage?.replace(/_/g, " "),
    count: s.count,
  }));

  const resumeData = (data.resume_performance || []).map((r: any) => ({
    name: r.version_label,
    ats: r.ats_score_avg || 0,
    apps: r.applications_used || 0,
    callback: r.callback_rate || 0,
  }));

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <BarChart3 className="w-6 h-6 text-violet-400" /> Analytics
        </h1>
        <p className="text-sm text-gray-400 mt-0.5">Your job search performance over time</p>
      </div>

      {/* Weekly applications chart */}
      <Section title="Weekly Activity" subtitle="Applications submitted vs callbacks received">
        {weeklyData.length < 2 ? (
          <Empty msg="Need 2+ weeks of data to show trends." />
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={weeklyData}>
              <XAxis dataKey="week" stroke="#6b7280" tick={{ fontSize: 11 }} />
              <YAxis stroke="#6b7280" tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }} />
              <Legend />
              <Line type="monotone" dataKey="apps" stroke="#7c3aed" strokeWidth={2} name="Applications" dot={false} />
              <Line type="monotone" dataKey="callbacks" stroke="#10b981" strokeWidth={2} name="Callbacks" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Source performance */}
        <Section title="Source Performance" subtitle="Where your callbacks actually come from">
          {sourceData.length === 0 ? <Empty msg="Log applications with sources to see this." /> : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={sourceData} layout="vertical">
                <XAxis type="number" stroke="#6b7280" tick={{ fontSize: 10 }} />
                <YAxis type="category" dataKey="name" stroke="#6b7280" tick={{ fontSize: 10 }} width={90} />
                <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
                  formatter={(val: any, name: string) => [name === "rate" ? `${val}%` : val, name]} />
                <Bar dataKey="applications" fill="#374151" name="Applications" />
                <Bar dataKey="callbacks" fill="#7c3aed" name="Callbacks" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Section>

        {/* Role category breakdown */}
        <Section title="Role Categories" subtitle="Where you're applying">
          {categoryData.length === 0 ? <Empty msg="Log applications to see category breakdown." /> : (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={categoryData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                  {categoryData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Section>
      </div>

      {/* Pipeline funnel */}
      <Section title="Pipeline Funnel" subtitle="Stage-by-stage conversion">
        {funnelData.length === 0 ? <Empty msg="No pipeline data yet." /> : (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={funnelData}>
              <XAxis dataKey="stage" stroke="#6b7280" tick={{ fontSize: 11 }} />
              <YAxis stroke="#6b7280" tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }} />
              <Bar dataKey="count" fill="#7c3aed" radius={[4, 4, 0, 0]} name="Applications" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </Section>

      {/* Resume performance */}
      {resumeData.length > 0 && (
        <Section title="Resume Performance" subtitle="Which resume version is converting best">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800">
                  {["Resume Version", "Avg ATS Score", "Applications", "Callback Rate"].map(h => (
                    <th key={h} className="text-left text-xs text-gray-400 font-medium pb-3 pr-6">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {resumeData.map((r: any, i: number) => (
                  <tr key={i} className="border-b border-gray-800/50">
                    <td className="py-3 pr-6 text-gray-200 font-medium">{r.name}</td>
                    <td className="py-3 pr-6">
                      <span className={`font-semibold ${r.ats >= 75 ? "text-green-400" : r.ats >= 50 ? "text-amber-400" : "text-red-400"}`}>
                        {Math.round(r.ats)}/100
                      </span>
                    </td>
                    <td className="py-3 pr-6 text-gray-300">{r.apps}</td>
                    <td className="py-3 pr-6">
                      <span className={r.callback >= 15 ? "text-green-400" : "text-amber-400"}>
                        {r.callback}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}
    </div>
  );
}

function Section({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <p className="font-semibold text-white">{title}</p>
      <p className="text-xs text-gray-400 mb-5">{subtitle}</p>
      {children}
    </div>
  );
}

function Empty({ msg }: { msg: string }) {
  return <p className="text-center text-sm text-gray-500 py-8">{msg}</p>;
}

function Skeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-8 w-40 bg-gray-800 rounded" />
      {[...Array(3)].map((_, i) => <div key={i} className="h-56 bg-gray-900 rounded-xl" />)}
    </div>
  );
}
