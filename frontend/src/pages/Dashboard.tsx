import { useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import { useLabStore } from "@/store/labStore";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { Trophy, Target, Flame } from "lucide-react";

export function Dashboard() {
  const { profile } = useAuthStore();
  const { labs, categories, fetchAll, isLoading } = useLabStore();

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const completed = labs.filter((l) => l.is_completed).length;
  const total = labs.length || 1;
  const pctComplete = Math.round((completed / total) * 100);

  return (
    <div className="mx-auto max-w-7xl px-6 py-12">
      <h1 className="font-display text-3xl text-void-100">
        Welcome back, <span className="text-brand-500">{profile?.display_name || profile?.username}</span>
      </h1>
      <p className="mt-1 text-void-400">Here's where you stand in the range.</p>

      <div className="mt-8 grid gap-6 sm:grid-cols-3">
        <Card>
          <CardContent className="flex items-center gap-4">
            <div className="rounded-md bg-success-500/10 p-3 text-success-400"><Trophy className="h-6 w-6" /></div>
            <div>
              <p className="text-2xl font-semibold text-void-100">{profile?.total_points ?? 0}</p>
              <p className="text-xs text-void-400">total points</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-4">
            <div className="rounded-md bg-brand-500/10 p-3 text-brand-400"><Target className="h-6 w-6" /></div>
            <div>
              <p className="text-2xl font-semibold text-void-100">{profile?.labs_completed ?? 0} / {labs.length}</p>
              <p className="text-xs text-void-400">labs completed</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-4">
            <div className="rounded-md bg-warning-500/10 p-3 text-warning-400"><Flame className="h-6 w-6" /></div>
            <div>
              <p className="text-2xl font-semibold text-void-100">{categories.length}</p>
              <p className="text-xs text-void-400">OWASP categories in progress</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="mt-8">
        <div className="mb-2 flex items-center justify-between text-sm text-void-400">
          <span>Overall progress</span>
          <span>{pctComplete}%</span>
        </div>
        <Progress value={pctComplete} />
      </div>

      <div className="mt-10 flex items-center justify-between">
        <h2 className="font-display text-xl text-void-100">Continue training</h2>
        <Button variant="ghost" size="sm" asChild>
          <Link to="/labs">View all labs →</Link>
        </Button>
      </div>

      {!isLoading && (
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {labs.filter((l) => !l.is_completed).slice(0, 3).map((lab) => (
            <Link key={lab.id} to={`/labs/${lab.slug}`}>
              <Card className="h-full transition-colors hover:border-brand-500/60">
                <CardContent>
                  <p className="font-mono text-xs text-void-400">{lab.category.code} · {lab.category.short_name}</p>
                  <h3 className="mt-1 font-display text-void-100">{lab.title}</h3>
                  <p className="mt-2 text-sm text-void-400">{lab.summary}</p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
