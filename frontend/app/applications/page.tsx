"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Plus, Filter, Search } from "lucide-react";
import { api, Application } from "@/lib/api";
import { ApplicationCard } from "@/components/applications/ApplicationCard";
import { AddApplicationModal } from "@/components/applications/AddApplicationModal";

const KANBAN_STAGES = [
  { id: "applied", label: "Applied", color: "border-gray-600" },
  { id: "screening", label: "Screening", color: "border-blue-500" },
  { id: "phone_screen", label: "Phone Screen", color: "border-cyan-500" },
  { id: "technical", label: "Technical", color: "border-violet-500" },
  { id: "case_study", label: "Case Study", color: "border-purple-500" },
  { id: "final", label: "Final Round", color: "border-amber-500" },
  { id: "offer", label: "Offer 🎉", color: "border-green-500" },
];

export default function ApplicationsPage() {
  const { getToken } = useAuth();
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [view, setView] = useState<"kanban" | "list">("kanban");
  const [search, setSearch] = useState("");
  const [dragOverStage, setDragOverStage] = useState<string | null>(null);

  const load = async () => {
    const token = await getToken();
    if (!token) return;
    const resp = await api.listApplications(token);
    if (resp.data) setApplications(resp.data);
    setLoading(false);
  };

  useEffect(() => { load(); }, [getToken]); // eslint-disable-line react-hooks/exhaustive-deps

  // Check URL params for ?action=add
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("action") === "add") setShowAddModal(true);
  }, []);

  const filteredApps = applications.filter(
    (a) =>
      a.company_name.toLowerCase().includes(search.toLowerCase()) ||
      a.role_title.toLowerCase().includes(search.toLowerCase())
  );

  const getStageApps = (stageId: string) =>
    filteredApps.filter((a) => a.stage === stageId);

  const handleAppAdded = (app: Application) => {
    setApplications((prev) => [app, ...prev]);
    setShowAddModal(false);
  };

  const handleStageChange = async (id: string, newStage: string) => {
    const prevApps = applications;
    // Optimistic update
    setApplications((prev) => prev.map((a) => a.id === id ? { ...a, stage: newStage } : a));
    try {
      const token = await getToken();
      if (!token) { setApplications(prevApps); return; }
      const resp = await api.updateApplication(token, id, { stage: newStage });
      if (resp.error) setApplications(prevApps);
    } catch {
      setApplications(prevApps);
    }
  };

  if (loading) return <ApplicationsSkeleton />;

  return (
    <div className="max-w-full">
      {/* ── Header ────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Applications</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            {applications.length} tracked · {applications.filter(a => !["rejected","ghosted","withdrawn"].includes(a.stage)).length} active
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* View toggle */}
          <div className="flex bg-gray-900 border border-gray-800 rounded-lg p-1">
            <button
              onClick={() => setView("kanban")}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${view === "kanban" ? "bg-gray-700 text-white" : "text-gray-400"}`}
            >
              Kanban
            </button>
            <button
              onClick={() => setView("list")}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${view === "list" ? "bg-gray-700 text-white" : "text-gray-400"}`}
            >
              List
            </button>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Application
          </button>
        </div>
      </div>

      {/* ── Search ────────────────────────────────────────────────── */}
      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
        <input
          type="text"
          placeholder="Search company or role..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 bg-gray-900 border border-gray-800 rounded-lg text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-gray-600 transition-colors"
        />
      </div>

      {/* ── Kanban Board ──────────────────────────────────────────── */}
      {view === "kanban" && (
        <div className="flex gap-3 overflow-x-auto pb-4 scrollbar-thin">
          {KANBAN_STAGES.map((stage) => {
            const stageApps = getStageApps(stage.id);
            return (
              <div
                key={stage.id}
                className={`shrink-0 w-52 rounded-xl transition-colors ${dragOverStage === stage.id ? "bg-violet-500/10 ring-1 ring-violet-500/40" : ""}`}
                onDragOver={(e) => { e.preventDefault(); setDragOverStage(stage.id); }}
                onDragLeave={() => setDragOverStage(null)}
                onDrop={(e) => {
                  e.preventDefault();
                  const id = e.dataTransfer.getData("applicationId");
                  if (id) handleStageChange(id, stage.id);
                  setDragOverStage(null);
                }}
              >
                {/* Column header */}
                <div className={`flex items-center justify-between mb-3 pb-2 border-b-2 ${stage.color}`}>
                  <span className="text-sm font-semibold text-gray-200">{stage.label}</span>
                  <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded-full">
                    {stageApps.length}
                  </span>
                </div>

                {/* Cards */}
                <div className="space-y-3">
                  {stageApps.length === 0 ? (
                    <div className="h-16 border border-dashed border-gray-800/60 rounded-xl flex items-center justify-center opacity-40">
                      <span className="text-xs text-gray-600">Empty</span>
                    </div>
                  ) : (
                    stageApps.map((app) => (
                      <ApplicationCard key={app.id} application={app} compact onStageChange={handleStageChange} />
                    ))
                  )}
                </div>
              </div>
            );
          })}

          {/* Graveyard */}
          <div
            className={`shrink-0 w-44 transition-colors ${dragOverStage === "rejected" ? "bg-red-500/10 ring-1 ring-red-500/40 rounded-xl" : ""}`}
            onDragOver={(e) => { e.preventDefault(); setDragOverStage("rejected"); }}
            onDragLeave={() => setDragOverStage(null)}
            onDrop={(e) => {
              e.preventDefault();
              const id = e.dataTransfer.getData("applicationId");
              if (id) handleStageChange(id, "rejected");
              setDragOverStage(null);
            }}
          >
            <div className="flex items-center justify-between mb-3 pb-2 border-b-2 border-gray-700">
              <span className="text-sm font-medium text-gray-400">Closed</span>
              <span className="text-xs text-gray-600 bg-gray-900 px-2 py-0.5 rounded-full">
                {filteredApps.filter(a => ["rejected", "ghosted", "withdrawn"].includes(a.stage)).length}
              </span>
            </div>
            <div className="space-y-2">
              {filteredApps
                .filter(a => ["rejected", "ghosted", "withdrawn"].includes(a.stage))
                .slice(0, 5)
                .map((app) => (
                  <ApplicationCard key={app.id} application={app} compact onStageChange={handleStageChange} />
                ))}
            </div>
          </div>
        </div>
      )}

      {/* ── List View ─────────────────────────────────────────────── */}
      {view === "list" && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredApps.map((app) => (
            <ApplicationCard key={app.id} application={app} onStageChange={handleStageChange} />
          ))}
        </div>
      )}

      {/* ── Empty state ───────────────────────────────────────────── */}
      {filteredApps.length === 0 && !loading && (
        <div className="text-center py-16">
          <p className="text-gray-500 mb-4">No applications yet. Start tracking your job hunt.</p>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 bg-violet-600 text-white text-sm rounded-lg hover:bg-violet-500 transition-colors"
          >
            Add Your First Application
          </button>
        </div>
      )}

      {/* ── Add Modal ─────────────────────────────────────────────── */}
      {showAddModal && (
        <AddApplicationModal
          onClose={() => setShowAddModal(false)}
          onAdded={handleAppAdded}
        />
      )}
    </div>
  );
}

function ApplicationsSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="h-8 w-48 bg-gray-800 rounded" />
      <div className="flex gap-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="w-72 shrink-0 space-y-3">
            <div className="h-4 bg-gray-800 rounded" />
            {[...Array(3)].map((_, j) => (
              <div key={j} className="h-24 bg-gray-900 rounded-xl" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
