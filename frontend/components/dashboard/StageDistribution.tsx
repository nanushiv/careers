"use client";

const STAGE_COLORS: Record<string, string> = {
  applied: "bg-gray-600",
  screening: "bg-blue-500",
  phone_screen: "bg-cyan-500",
  technical: "bg-violet-500",
  case_study: "bg-purple-500",
  final: "bg-amber-500",
  offer: "bg-emerald-400",
};

const STAGE_LABELS: Record<string, string> = {
  applied: "Applied",
  screening: "Screening",
  phone_screen: "Phone Screen",
  technical: "Technical",
  case_study: "Case Study",
  final: "Final Round",
  offer: "🎉 Offer",
};

export function StageDistribution({ distribution }: { distribution: Record<string, number> }) {
  const total = Object.values(distribution).reduce((a, b) => a + b, 0);
  if (total === 0) return (
    <p className="text-sm text-gray-500 text-center py-4">No active applications</p>
  );

  return (
    <div className="space-y-2.5">
      {Object.entries(distribution).map(([stage, count]) => {
        const isOffer = stage === "offer";
        return (
          <div key={stage} className={`flex items-center gap-2 ${isOffer && count > 0 ? "relative" : ""}`}>
            <div className={`w-2 h-2 rounded-full shrink-0 ${STAGE_COLORS[stage] || "bg-gray-600"} ${isOffer && count > 0 ? "shadow-[0_0_6px_#34d399]" : ""}`} />
            <span className={`text-xs capitalize flex-1 ${isOffer && count > 0 ? "text-emerald-300 font-medium" : "text-gray-400"}`}>
              {STAGE_LABELS[stage] || stage.replace(/_/g, " ")}
            </span>
            <span className={`text-xs font-medium ${isOffer && count > 0 ? "text-emerald-300" : "text-gray-200"}`}>{count}</span>
            <div className="w-16 h-1.5 bg-gray-800 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${STAGE_COLORS[stage] || "bg-gray-600"}`}
                style={{
                  width: `${(count / total) * 100}%`,
                  boxShadow: isOffer && count > 0 ? "0 0 4px #34d399" : undefined,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
