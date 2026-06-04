"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import {
  Briefcase, MapPin, ExternalLink, Bookmark, Lock,
  RefreshCw, Loader2, Building2, Zap, TrendingUp
} from "lucide-react";
import Link from "next/link";

interface Job {
  job_id: string;
  title: string;
  company: string;
  location: string;
  remote: boolean;
  url: string;
  snippet: string;
  fit_score: number;
  fit_reason: string;
  posted_date: string;
  yoe_label?: string;
}

export default function JobsPage() {
  const { getToken } = useAuth();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [isPro, setIsPro] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [locationNote, setLocationNote] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "high">("all");
  const [searchLocation, setSearchLocation] = useState("");
  const [authToken, setAuthToken] = useState("");

  const load = async (loc = "") => {
    setLoading(true);
    setApiError(null);
    setLocationNote(null);
    try {
      const token = await getToken();
      if (!token) return;
      setAuthToken(token);

      const params = new URLSearchParams({ limit: "50" });
      if (loc.trim()) params.set("location", loc.trim());

      const resp = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/jobs/suggestions?${params}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const data = await resp.json();

      if (resp.status === 402) {
        setIsPro(false);
      } else {
        // Any non-402 response = user has access
        setIsPro(true);
        if (data.success) {
          const decodeHtml = (s: string) => s?.replace(/&#(\d+);/g, (_, n) => String.fromCharCode(n)).replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"') ?? s;
          setJobs((data.data.jobs || []).map((j: Job) => ({ ...j, title: decodeHtml(j.title), company: decodeHtml(j.company), snippet: decodeHtml(j.snippet) })));
          setLocationNote(data.data.location_note || null);
        } else {
          setApiError(data.detail || data.error?.message || "Something went wrong. Try again.");
        }
      }
    } catch (e) {
      console.error(e);
      setApiError("Failed to load jobs. Check your connection.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const filtered = jobs.filter(j => {
    if (filter === "high" && j.fit_score < 70) return false;
    return true;
  });

  const scoreColor = (s: number) =>
    s >= 75 ? "text-green-400 bg-green-500/10 border-green-500/20"
    : s >= 55 ? "text-amber-400 bg-amber-500/10 border-amber-500/20"
    : "text-red-400 bg-red-500/10 border-red-500/20";

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Briefcase className="w-6 h-6 text-violet-400" /> Job Matches
          </h1>
          <p className="text-sm text-gray-400 mt-0.5">
            AI-matched roles based on your resume — updated daily
          </p>
        </div>
        {isPro && (
          <button onClick={() => load()} disabled={loading}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-gray-200 bg-gray-800 border border-gray-700 rounded-lg transition-colors">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        )}
      </div>

      {/* Loading state (shown regardless of plan) */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-24 gap-3">
          <Loader2 className="w-8 h-8 text-violet-400 animate-spin" />
          <p className="text-sm text-gray-400">Finding matching roles for your profile...</p>
        </div>
      )}

      {/* Pro gate */}
      {!isPro && !loading && <ProGate />}

      {isPro && !loading && (
        <>
          {/* Filters */}
          <div className="flex items-center gap-3 mb-5 flex-wrap">
            <div className="flex gap-1 bg-gray-900 border border-gray-800 rounded-lg p-1">
              {[
                { id: "all", label: "All matches" },
                { id: "high", label: "Strong fit (70+)" },
              ].map(f => (
                <button key={f.id} onClick={() => setFilter(f.id as any)}
                  className={`px-3 py-1.5 text-xs font-medium rounded transition-all ${
                    filter === f.id ? "bg-violet-600 text-white" : "text-gray-400 hover:text-gray-200"
                  }`}>
                  {f.label}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-gray-500" />
              <input
                value={searchLocation}
                onChange={e => setSearchLocation(e.target.value)}
                onKeyDown={e => e.key === "Enter" && load(searchLocation)}
                placeholder="Country or Remote…"
                className="px-2.5 py-1.5 text-xs bg-gray-900 border border-gray-700 rounded-lg text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-violet-500 w-44"
              />
              <button onClick={() => load(searchLocation)}
                className="px-2.5 py-1.5 text-xs bg-gray-800 text-gray-300 rounded-lg border border-gray-700 hover:bg-gray-700 transition-colors">
                Search
              </button>
            </div>

            <span className="text-xs text-gray-500 ml-auto">
              {filtered.length} roles found
            </span>
          </div>

          {/* Location note banner */}
          {locationNote && (
            <div className="flex items-start gap-2 px-4 py-3 mb-4 bg-amber-500/10 border border-amber-500/20 rounded-xl text-xs text-amber-300">
              <MapPin className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              <span>{locationNote}</span>
            </div>
          )}

          {/* Job list */}
          {apiError ? (
            <div className="text-center py-16 bg-gray-900 border border-red-500/20 border-dashed rounded-2xl">
              <Briefcase className="w-10 h-10 text-red-400 mx-auto mb-3" />
              <p className="text-gray-300 font-medium mb-1">Could not load jobs</p>
              <p className="text-sm text-gray-500 mb-4">{apiError}</p>
              <button onClick={() => load()} className="px-4 py-2 bg-gray-800 text-gray-300 text-sm rounded-lg border border-gray-700 hover:bg-gray-700 transition-colors">
                Try again
              </button>
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-16 bg-gray-900 border border-gray-800 border-dashed rounded-2xl">
              <Briefcase className="w-10 h-10 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400">No jobs found. Try a different location or filter.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filtered.map(job => (
                <JobCard key={job.job_id} job={job} scoreColor={scoreColor} token={authToken} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function JobCard({ job, scoreColor, token }: { job: Job; scoreColor: (s: number) => string; token: string }) {
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (saved || saving) return;
    setSaving(true);
    try {
      await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/jobs/save/${job.job_id}`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
          body: JSON.stringify({ title: job.title, company: job.company, url: job.url, fit_score: job.fit_score }),
        }
      );
      setSaved(true);
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-700 transition-all">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3 min-w-0">
          <div className="w-10 h-10 rounded-lg bg-gray-800 border border-gray-700 flex items-center justify-center shrink-0">
            <Building2 className="w-5 h-5 text-gray-400" />
          </div>
          <div className="min-w-0">
            <p className="font-semibold text-gray-100">{job.title}</p>
            <p className="text-sm text-gray-400">{job.company}</p>
            <div className="flex items-center gap-3 mt-1 flex-wrap">
              <span className="flex items-center gap-1 text-xs text-gray-500">
                <MapPin className="w-3 h-3" />{job.location}
              </span>
              {job.remote && (
                <span className="text-xs px-1.5 py-0.5 bg-blue-500/10 text-blue-300 rounded border border-blue-500/20">
                  Remote
                </span>
              )}
              {job.posted_date && (
                <span className="text-xs text-gray-600">{job.posted_date}</span>
              )}
            </div>
          </div>
        </div>

        {/* Fit score */}
        <div className={`shrink-0 text-center px-3 py-2 rounded-lg border text-xs font-bold ${scoreColor(job.fit_score)}`}>
          <p className="text-lg leading-none">{Math.round(job.fit_score)}</p>
          <p className="opacity-70 mt-0.5">fit</p>
        </div>
      </div>

      {/* Snippet */}
      {job.snippet && (
        <p className="text-xs text-gray-400 mt-3 line-clamp-2">{job.snippet}</p>
      )}

      {/* Experience badge */}
      {job.yoe_label && (
        <div className={`inline-flex items-center gap-1 mt-2 px-2 py-0.5 rounded-full text-xs font-medium ${
          job.yoe_label.startsWith("✓")
            ? "bg-green-500/10 text-green-400 border border-green-500/20"
            : job.yoe_label.startsWith("⚡")
            ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
            : "bg-gray-800 text-gray-400 border border-gray-700"
        }`}>
          {job.yoe_label}
        </div>
      )}

      {/* Fit reason */}
      <div className="flex items-center gap-1 mt-2">
        <Zap className="w-3 h-3 text-violet-400" />
        <p className="text-xs text-violet-300">{job.fit_reason}</p>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 mt-4 pt-3 border-t border-gray-800">
        <a href={`https://www.linkedin.com/jobs/search/?keywords=${encodeURIComponent(job.title + " " + job.company)}`}
          target="_blank" rel="noopener noreferrer"
          className="flex items-center gap-1.5 px-3 py-1.5 bg-violet-600 hover:bg-violet-500 text-white text-xs font-medium rounded-lg transition-colors">
          Search on LinkedIn <ExternalLink className="w-3 h-3" />
        </a>
        <button onClick={handleSave} disabled={saved || saving}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
            saved ? "bg-green-600/20 border-green-500/30 text-green-300"
                  : "border-gray-700 text-gray-400 hover:border-gray-600 hover:text-gray-200"
          }`}>
          <Bookmark className={`w-3 h-3 ${saved ? "fill-current" : ""}`} />
          {saving ? "Saving…" : saved ? "Saved ✓" : "Save to tracker"}
        </button>
        <Link href="/outreach"
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-gray-700 text-gray-400 hover:border-gray-600 rounded-lg transition-colors ml-auto">
          <TrendingUp className="w-3 h-3" /> Draft outreach
        </Link>
      </div>
    </div>
  );
}

function ProGate() {
  return (
    <div className="text-center py-20 bg-gray-900 border border-gray-800 rounded-2xl">
      <div className="w-16 h-16 bg-violet-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
        <Lock className="w-8 h-8 text-violet-400" />
      </div>
      <h2 className="text-xl font-bold text-white mb-2">Pro Feature</h2>
      <p className="text-gray-400 max-w-sm mx-auto mb-6">
        Get AI-matched job suggestions based on your resume — ranked by fit score so you apply smarter, not more.
      </p>
      <div className="flex flex-wrap justify-center gap-3 text-sm text-gray-300 mb-8">
        {["Matched to your resume", "Ranked by fit score", "Updated daily", "One-click apply"].map(f => (
          <span key={f} className="flex items-center gap-1">
            <span className="text-violet-400">✓</span> {f}
          </span>
        ))}
      </div>
      <Link href="/pricing"
        className="inline-flex items-center gap-2 px-6 py-3 bg-violet-600 hover:bg-violet-500 text-white font-semibold rounded-xl transition-colors">
        Upgrade to Pro — ₹999/mo
      </Link>
    </div>
  );
}
