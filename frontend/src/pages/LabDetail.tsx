import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { api } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import type { LabDetail as LabDetailType } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DifficultyBadge, Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ExternalLink, Lock, Unlock, Flag, BookOpen, CheckCircle2 } from "lucide-react";

export function LabDetail() {
  const { slug } = useParams<{ slug: string }>();
  const { profile } = useAuthStore();

  const [lab, setLab] = useState<LabDetailType | null>(null);
  const [flag, setFlag] = useState("");
  const [feedback, setFeedback] = useState<{ ok: boolean; text: string } | null>(null);
  const [solution, setSolution] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    if (!slug) return;
    const { data } = await api.get<LabDetailType>(`/labs/${slug}/`);
    setLab(data);
  }, [slug]);

  useEffect(() => {
    load();
  }, [load]);

  async function submitFlag(e: React.FormEvent) {
    e.preventDefault();
    if (!slug || !flag.trim()) return;
    setSubmitting(true);
    setFeedback(null);
    try {
      const { data } = await api.post(`/labs/${slug}/submit/`, { flag });
      setFeedback(
        data.is_correct
          ? { ok: true, text: `Correct! +${data.points_awarded} points.` }
          : { ok: false, text: "Not quite — that flag doesn't match." }
      );
      if (data.is_correct) await load();
    } catch {
      setFeedback({ ok: false, text: "Incorrect flag. Keep digging." });
    } finally {
      setSubmitting(false);
      setFlag("");
    }
  }

  async function unlockHint(hintId: number) {
    if (!slug) return;
    const { data } = await api.post(`/labs/${slug}/hints/${hintId}/unlock/`);
    setLab((prev) =>
      prev
        ? { ...prev, hints: prev.hints.map((h) => (h.id === hintId ? { ...h, is_unlocked: true, text: data.text } : h)) }
        : prev
    );
  }

  async function viewSolution() {
    if (!slug) return;
    const { data } = await api.get(`/labs/${slug}/solution/`);
    setSolution(data.content);
  }

  if (!lab) {
    return <p className="mx-auto max-w-4xl px-6 py-20 font-mono text-void-400 animate-flicker">loading lab...</p>;
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      <div className="flex flex-wrap items-center gap-3">
        <Badge tone="brand">{lab.category.code} · {lab.category.short_name}</Badge>
        <DifficultyBadge difficulty={lab.difficulty} />
        {lab.is_completed && <Badge tone="success" className="flex items-center gap-1"><CheckCircle2 className="h-3 w-3" /> completed</Badge>}
      </div>
      <h1 className="mt-3 font-display text-3xl text-void-100">{lab.title}</h1>
      <p className="mt-2 text-void-400">{lab.summary}</p>

      <div className="mt-6 flex flex-wrap items-center gap-4 text-sm text-void-400">
        <span className="font-mono text-success-400">{lab.points} pts</span>
        <span>~{lab.estimated_minutes} min</span>
        <span>{lab.attempts} attempt{lab.attempts === 1 ? "" : "s"}</span>
      </div>

      {lab.target_url && (
        <a href={lab.target_url} target="_blank" rel="noreferrer">
          <Button className="mt-6" variant="secondary">
            <ExternalLink className="h-4 w-4" /> Open live target
          </Button>
        </a>
      )}

      <Card className="mt-8">
        <CardHeader><CardTitle>Briefing</CardTitle></CardHeader>
        <CardContent className="prose-invert max-w-none text-sm leading-relaxed text-void-200">
          <ReactMarkdown>{lab.briefing}</ReactMarkdown>
        </CardContent>
      </Card>

      <Card className="mt-6">
        <CardHeader><CardTitle>Objective</CardTitle></CardHeader>
        <CardContent className="text-sm text-void-200">{lab.objective}</CardContent>
      </Card>

      {lab.hints.length > 0 && (
        <Card className="mt-6">
          <CardHeader><CardTitle>Hints</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {lab.hints.map((hint) => (
              <div key={hint.id} className="rounded-md border border-void-600 p-3">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-void-400">Hint {hint.order} · -{hint.point_penalty} pts</span>
                  {!hint.is_unlocked && (
                    <Button size="sm" variant="ghost" onClick={() => unlockHint(hint.id)}>
                      <Lock className="h-3.5 w-3.5" /> unlock
                    </Button>
                  )}
                </div>
                {hint.is_unlocked && (
                  <p className="mt-2 flex items-start gap-2 text-sm text-void-200">
                    <Unlock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success-400" /> {hint.text}
                  </p>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <Card className="mt-6 border-brand-500/30">
        <CardHeader><CardTitle className="flex items-center gap-2"><Flag className="h-4 w-4 text-brand-400" /> Submit flag</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={submitFlag} className="flex gap-3">
            <Input
              value={flag}
              onChange={(e) => setFlag(e.target.value)}
              placeholder="VOIDLAB{...}"
              className="font-mono"
            />
            <Button type="submit" disabled={submitting}>{submitting ? "checking..." : "Submit"}</Button>
          </form>
          {feedback && (
            <p className={`mt-3 text-sm ${feedback.ok ? "text-success-400" : "text-danger-400"}`}>{feedback.text}</p>
          )}
        </CardContent>
      </Card>

      {profile?.is_admin_operator && lab.has_solution && (
        <Card className="mt-6 border-warning-500/30">
          <CardHeader><CardTitle className="flex items-center gap-2 text-warning-400"><BookOpen className="h-4 w-4" /> Solution (admin only)</CardTitle></CardHeader>
          <CardContent>
            {solution ? (
              <div className="prose-invert max-w-none text-sm text-void-200"><ReactMarkdown>{solution}</ReactMarkdown></div>
            ) : (
              <Button variant="outline" onClick={viewSolution}>Reveal walkthrough</Button>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
