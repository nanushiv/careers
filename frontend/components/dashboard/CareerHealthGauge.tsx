"use client";

import { useEffect, useRef } from "react";

interface CareerHealthGaugeProps {
  score: number; // 0-100
}

const getColor = (score: number) => {
  if (score >= 80) return { stroke: "#22c55e", text: "#4ade80", label: "Top Shape", sub: "Keep applying!" };
  if (score >= 65) return { stroke: "#10b981", text: "#34d399", label: "Strong", sub: "On the right track" };
  if (score >= 50) return { stroke: "#f59e0b", text: "#fbbf24", label: "Building", sub: "Keep going" };
  if (score >= 30) return { stroke: "#f97316", text: "#fb923c", label: "Early Stage", sub: "Log more activity" };
  return { stroke: "#ef4444", text: "#f87171", label: "Needs Work", sub: "Start with your resume" };
};

export function CareerHealthGauge({ score }: CareerHealthGaugeProps) {
  const { stroke, text, label, sub } = getColor(score);

  // SVG arc math
  const size = 140;
  const strokeWidth = 12;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  // Only fill 75% of the circle (gauge, not full circle)
  const gaugePortion = 0.75;
  const offset = circumference * (1 - gaugePortion * (score / 100));
  const rotation = -135; // Start at bottom-left

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative">
        <svg width={size} height={size} className="-rotate-[45deg]">
          {/* Track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#1f2937"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={`${circumference * gaugePortion} ${circumference}`}
          />
          {/* Progress */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={stroke}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={`${circumference * gaugePortion * (score / 100)} ${circumference}`}
            className="transition-all duration-1000 ease-out"
            style={{
              filter: `drop-shadow(0 0 6px ${stroke}66)`,
            }}
          />
        </svg>
        {/* Center score */}
        <div className="absolute inset-0 flex flex-col items-center justify-center rotate-[45deg]">
          <span className="text-3xl font-bold" style={{ color: text }}>
            {Math.round(score)}
          </span>
          <span className="text-xs text-gray-500 -mt-1">/ 100</span>
        </div>
      </div>
      <div className="text-center">
        <span
          className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold"
          style={{ backgroundColor: `${stroke}22`, color: text }}
        >
          {label}
        </span>
        <p className="text-xs mt-1" style={{ color: `${stroke}99` }}>{sub}</p>
      </div>
    </div>
  );
}
