import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useLabStore } from "@/store/labStore";
import { Card, CardContent } from "@/components/ui/card";
import { DifficultyBadge } from "@/components/ui/badge";
import { CheckCircle2, Clock } from "lucide-react";
import { cn } from "@/lib/utils";

export function Labs() {
  const { labs, categories, fetchAll, isLoading } = useLabStore();
  const [activeCategory, setActiveCategory] = useState<string | null>(null);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const filtered = useMemo(
    () => (activeCategory ? labs.filter((l) => l.category.code === activeCategory) : labs),
    [labs, activeCategory]
  );

  return (
    <div className="mx-auto max-w-7xl px-6 py-12">
      <h1 className="font-display text-3xl text-void-100">Lab catalog</h1>
      <p className="mt-1 text-void-400">Structured challenges across every OWASP Top 10:2025 category.</p>

      <div className="mt-6 flex flex-wrap gap-2">
        <button
          onClick={() => setActiveCategory(null)}
          className={cn(
            "rounded-full border px-3 py-1 text-xs font-mono transition-colors",
            activeCategory === null ? "border-brand-500 bg-brand-500/15 text-brand-400" : "border-void-600 text-void-400 hover:text-void-100"
          )}
        >
          all
        </button>
        {categories.map((c) => (
          <button
            key={c.code}
            onClick={() => setActiveCategory(c.code)}
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-mono transition-colors",
              activeCategory === c.code ? "border-brand-500 bg-brand-500/15 text-brand-400" : "border-void-600 text-void-400 hover:text-void-100"
            )}
          >
            {c.code}
          </button>
        ))}
      </div>

      {isLoading ? (
        <p className="mt-10 font-mono text-void-400 animate-flicker">loading catalog...</p>
      ) : (
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((lab) => (
            <Link key={lab.id} to={`/labs/${lab.slug}`}>
              <Card className="h-full transition-colors hover:border-brand-500/60">
                <CardContent>
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-mono text-xs text-void-400">{lab.category.code} · {lab.category.short_name}</p>
                    {lab.is_completed && <CheckCircle2 className="h-4 w-4 shrink-0 text-success-500" />}
                  </div>
                  <h3 className="mt-1 font-display text-void-100">{lab.title}</h3>
                  <p className="mt-2 line-clamp-2 text-sm text-void-400">{lab.summary}</p>
                  <div className="mt-4 flex items-center justify-between">
                    <DifficultyBadge difficulty={lab.difficulty} />
                    <div className="flex items-center gap-3 text-xs text-void-400">
                      <span className="flex items-center gap-1"><Clock className="h-3.5 w-3.5" /> {lab.estimated_minutes}m</span>
                      <span className="font-mono text-success-400">{lab.points} pts</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
