import React from "react";
import { cn } from "@/lib/utils";
import type { Difficulty } from "@/types";

type Tone = "brand" | "success" | "warning" | "danger" | "neutral";

const toneClasses: Record<Tone, string> = {
  brand: "bg-brand-500/15 text-brand-400 border-brand-500/30",
  success: "bg-success-500/15 text-success-400 border-success-500/30",
  warning: "bg-warning-500/15 text-warning-400 border-warning-500/30",
  danger: "bg-danger-500/15 text-danger-400 border-danger-500/30",
  neutral: "bg-void-700 text-void-400 border-void-600",
};

export function Badge({ tone = "neutral", className, ...props }: React.HTMLAttributes<HTMLSpanElement> & { tone?: Tone }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium uppercase tracking-wider",
        toneClasses[tone],
        className
      )}
      {...props}
    />
  );
}

const difficultyTone: Record<Difficulty, Tone> = {
  easy: "success",
  medium: "warning",
  hard: "danger",
  insane: "danger",
};

export function DifficultyBadge({ difficulty }: { difficulty: Difficulty }) {
  return (
    <Badge tone={difficultyTone[difficulty]} className={difficulty === "insane" ? "animate-pulse-glow" : ""}>
      {difficulty}
    </Badge>
  );
}
