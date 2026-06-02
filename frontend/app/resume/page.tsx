"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useAuth } from "@clerk/nextjs";
import { useDropzone } from "react-dropzone";
import {
  Upload, FileText, Star, Trash2, Brain, Loader2, CheckCircle2
} from "lucide-react";
import { api, Resume } from "@/lib/api";
import { formatDistanceToNow } from "date-fns";

export default function ResumePage() {
  const { getToken } = useAuth();
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [jdModal, setJdModal] = useState<Resume | null>(null);
  const [jdText, setJdText] = useState("");
  const pollingRef = useRef<Record<string, NodeJS.Timeout>>({});

  const load = async () => {
    const token = await getToken();
    if (!token) return;
    const resp = await api.listResumes(token);
    if (resp.data) setResumes(resp.data);
    setLoading(false);
  };

  useEffect(() => {
    load();
    return () => {
      // Clear all polling on unmount
      Object.values(pollingRef.current).forEach(clearInterval);
    };
  }, []);

  // Poll a single resume until parse_status === "completed" | "failed"
  const pollParseStatus = useCallback((resumeId: string) => {
    if (pollingRef.current[resumeId]) return; // already polling

    const interval = setInterval(async () => {
      const token = await getToken();
      if (!token) return;
      const resp = await api.listResumes(token);
      if (!resp.data) return;
      const updated = resp.data.find((r) => r.id === resumeId);
      if (!updated) return;

      if (updated.parse_status === "completed" || updated.parse_status === "failed") {
        clearInterval(pollingRef.current[resumeId]);
        delete pollingRef.current[resumeId];
        setResumes((prev) => prev.map((r) => r.id === resumeId ? updated : r));
      }
    }, 2500);

    pollingRef.current[resumeId] = interval;

    // Safety timeout: stop after 2 minutes
    setTimeout(() => {
      if (pollingRef.current[resumeId]) {
        clearInterval(pollingRef.current[resumeId]);
        delete pollingRef.current[resumeId];
      }
    }, 120000);
  }, [getToken]);

  const onDrop = useCallback(async (files: File[]) => {
    const file = files[0];
    if (!file) return;

    setUploading(true);
    setUploadProgress(0);

    try {
      const token = await getToken();
      if (!token) return;

      const formData = new FormData();
      formData.append("file", file);
      formData.append("version_label", file.name.replace(/\.[^.]+$/, ""));

      const resp = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/resumes/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      const data = await resp.json();
      if (data.success && data.data) {
        setResumes((prev) => [data.data, ...prev]);
        setUploadProgress(100);
        // Start polling so "Run Analysis" button enables automatically
        pollParseStatus(data.data.id);
      }
    } catch (e) {
      console.error("Upload failed:", e);
    } finally {
      setUploading(false);
      setTimeout(() => setUploadProgress(0), 2000);
    }
  }, [getToken, pollParseStatus]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024,
  });

  const handleSetPrimary = async (id: string) => {
    const token = await getToken();
    if (!token) return;
    await api.setPrimaryResume(token, id);
    setResumes((prev) => prev.map((r) => ({ ...r, is_primary: r.id === id })));
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this resume version?")) return;
    const token = await getToken();
    if (!token) return;
    await api.deleteResume(token, id);
    setResumes((prev) => prev.filter((r) => r.id !== id));
  };

  const handleAnalyze = (resume: Resume) => {
    setJdText("");
    setJdModal(resume);
  };

  const runAnalysis = async () => {
    if (!jdModal) return;
    const token = await getToken();
    if (!token) return;
    setAnalyzing(jdModal.id);
    setJdModal(null);

    try {
      const analysisTypes = jdText.trim()
        ? ["ats", "recruiter", "readiness", "role_fit"]
        : ["recruiter", "readiness"];

      const resp = await api.triggerAnalysis(token, {
        resume_id: jdModal.id,
        analysis_types: analysisTypes,
        ...(jdText.trim() ? { jd_text: jdText.trim() } : {}),
      });

      if (resp.data?.job_id) {
        window.location.href = `/resume/${jdModal.id}/analysis?job=${resp.data.job_id}`;
      }
    } catch (e) {
      console.error("Analysis trigger failed:", e);
      setAnalyzing(null);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Resume Vault</h1>
        <p className="text-sm text-gray-400 mt-0.5">
          Manage resume versions and analyze them against job descriptions.
        </p>
      </div>

      {/* Upload Zone */}
      <div
        {...getRootProps()}
        className={`relative border-2 border-dashed rounded-2xl p-10 mb-8 text-center cursor-pointer transition-all ${
          isDragActive
            ? "border-violet-500 bg-violet-950/20"
            : "border-gray-700 hover:border-gray-600 bg-gray-900/50"
        }`}
      >
        <input {...getInputProps()} />
        {uploading ? (
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-10 h-10 text-violet-400 animate-spin" />
            <p className="text-sm text-gray-300">Uploading and parsing...</p>
            <div className="w-48 h-1.5 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-violet-500 rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </div>
        ) : (
          <>
            <Upload className="w-10 h-10 text-gray-500 mx-auto mb-4" />
            <p className="text-base font-medium text-gray-300">
              {isDragActive ? "Drop your resume here" : "Drop your resume, or click to browse"}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              PDF or DOCX · Max 10MB · AI parses in seconds
            </p>
          </>
        )}
      </div>

      {/* Resume List */}
      {loading ? (
        <div className="space-y-4">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="h-32 bg-gray-900 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : resumes.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <FileText className="w-10 h-10 mx-auto mb-3 opacity-40" />
          <p>No resumes uploaded yet. Drop your resume above to get started.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {resumes.map((resume) => (
            <ResumeCard
              key={resume.id}
              resume={resume}
              onSetPrimary={handleSetPrimary}
              onDelete={handleDelete}
              onAnalyze={handleAnalyze}
              isAnalyzing={analyzing === resume.id}
            />
          ))}
        </div>
      )}

      {/* JD Modal */}
      {jdModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 w-full max-w-lg">
            <h3 className="text-lg font-semibold text-white mb-1">Run AI Analysis</h3>
            <p className="text-sm text-gray-400 mb-4">
              Paste a job description for ATS keyword matching + Role Fit score. Skip to get Recruiter View + PM Readiness only.
            </p>
            <textarea
              value={jdText}
              onChange={e => setJdText(e.target.value)}
              placeholder="Paste job description here (optional)..."
              rows={8}
              className="w-full px-3 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-violet-500 resize-none"
            />
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => setJdModal(null)}
                className="flex-1 py-2.5 border border-gray-700 text-gray-400 rounded-xl text-sm hover:border-gray-600 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={runAnalysis}
                className="flex-1 py-2.5 bg-violet-600 hover:bg-violet-500 text-white rounded-xl text-sm font-medium transition-colors flex items-center justify-center gap-2"
              >
                <Brain className="w-4 h-4" />
                {jdText.trim() ? "Analyze with JD (4 analyses)" : "Analyze without JD (2 analyses)"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ResumeCard({
  resume,
  onSetPrimary,
  onDelete,
  onAnalyze,
  isAnalyzing,
}: {
  resume: Resume;
  onSetPrimary: (id: string) => void;
  onDelete: (id: string) => void;
  onAnalyze: (resume: Resume) => void;
  isAnalyzing: boolean;
}) {
  const isParsing = resume.parse_status === "pending" || resume.parse_status === "processing";

  const parseStatusEl = {
    completed: <span className="text-xs text-green-400 flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> Ready</span>,
    processing: <span className="text-xs text-amber-400 flex items-center gap-1"><Loader2 className="w-3 h-3 animate-spin" /> Parsing...</span>,
    pending: <span className="text-xs text-amber-400 flex items-center gap-1"><Loader2 className="w-3 h-3 animate-spin" /> Parsing...</span>,
    failed: <span className="text-xs text-red-400">Parse failed</span>,
  }[resume.parse_status] ?? null;

  return (
    <div className={`bg-gray-900 border rounded-xl p-5 transition-all ${
      resume.is_primary ? "border-violet-500/50" : "border-gray-800"
    }`}>
      <div className="flex items-start justify-between gap-4">
        {/* Info */}
        <div className="flex items-start gap-3 min-w-0">
          <div className="p-2 bg-gray-800 rounded-lg shrink-0 mt-0.5">
            <FileText className="w-5 h-5 text-violet-400" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="font-semibold text-gray-100 truncate">{resume.version_label}</p>
              {resume.is_primary && (
                <span className="text-xs px-2 py-0.5 bg-violet-500/20 text-violet-300 rounded-full border border-violet-500/30">
                  Primary
                </span>
              )}
              {parseStatusEl}
            </div>
            <p className="text-xs text-gray-500 mt-0.5">{resume.file_name}</p>

            {/* Stats */}
            <div className="flex items-center gap-4 mt-3">
              {resume.ats_score_avg && (
                <div className="text-center">
                  <p className="text-lg font-bold text-violet-400">{resume.ats_score_avg}</p>
                  <p className="text-xs text-gray-500">Avg ATS Score</p>
                </div>
              )}
              {resume.callback_rate !== null && resume.callback_rate !== undefined && (
                <div className="text-center">
                  <p className={`text-lg font-bold ${resume.callback_rate >= 15 ? "text-green-400" : "text-amber-400"}`}>
                    {resume.callback_rate}%
                  </p>
                  <p className="text-xs text-gray-500">Callback Rate</p>
                </div>
              )}
              <div className="text-center">
                <p className="text-lg font-bold text-gray-300">{resume.applications_used}</p>
                <p className="text-xs text-gray-500">Applications</p>
              </div>
              <div className="text-xs text-gray-500">
                Added {formatDistanceToNow(new Date(resume.created_at), { addSuffix: true })}
              </div>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 shrink-0">
          {!resume.is_primary && (
            <button
              onClick={() => onSetPrimary(resume.id)}
              className="p-2 rounded-lg text-gray-500 hover:text-amber-400 hover:bg-gray-800 transition-colors"
              title="Set as primary"
            >
              <Star className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={() => onAnalyze(resume)}
            disabled={isAnalyzing || isParsing}
            title={isParsing ? "Waiting for resume to finish parsing..." : "Run AI Analysis"}
            className="flex items-center gap-2 px-3 py-1.5 bg-violet-600/20 hover:bg-violet-600/30 disabled:opacity-40 disabled:cursor-not-allowed text-violet-300 text-xs font-medium rounded-lg border border-violet-500/30 transition-colors"
          >
            {isAnalyzing ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : isParsing ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Brain className="w-3.5 h-3.5" />
            )}
            {isAnalyzing ? "Analyzing..." : isParsing ? "Parsing..." : "Run Analysis"}
          </button>
          <button
            onClick={() => onDelete(resume.id)}
            className="p-2 rounded-lg text-gray-600 hover:text-red-400 hover:bg-gray-800 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
