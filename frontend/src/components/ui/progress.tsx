import { cn } from "@/lib/utils";

export function Progress({ value, className }: { value: number; className?: string }) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className={cn("h-2 w-full overflow-hidden rounded-full bg-void-700", className)}>
      <div
        className="h-full rounded-full bg-gradient-to-r from-brand-600 via-brand-500 to-success-500 transition-all duration-500"
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}
