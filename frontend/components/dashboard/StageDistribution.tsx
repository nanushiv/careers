"use client";

const STAGE_COLORS: Record<string, string> = {
  applied: "bg-gray-600",
  screening: "bg-blue-500",
  phone_screen: "bg-cyan-500",
  technical: "bg-violet-500",
  case_study: "bg-purple-500",
  final: "bg-amber-500",
  offer: "bg-green-500",
};

export function StageDistribution({ distribution }: { distribution: Record<string, number> }) {
  const total = Object.values(distribution).reduce((a, b) => a + b, 0);
  if (total === 0) return (
    <p className="text-sm text-gray-500 text-center py-4">No active applications</p>
  );

  return (
    <div className="space-y-2.5">
      {Object.entries(distribution).map(([stage, count]) => (
        <div key={stage} className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full shrink-0 ${STAGE_COLORS[stage] || "bg-gray-600"}`} />
          <span className="text-xs text-gray-400 capitalize flex-1">
            {stage.replace(/_/g, " ")}
          </span>
          <span className="text-xs font-medium text-gray-200">{count}</span>
          <div className="w-16 h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${STAGE_COLORS[stage] || "bg-gray-600"}`}
              style={{ width: `${(count / total) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
