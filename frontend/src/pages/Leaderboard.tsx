import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import type { LeaderboardRow } from "@/types";
import { Card, CardContent } from "@/components/ui/card";
import { Trophy, Medal } from "lucide-react";
import { cn } from "@/lib/utils";

export function Leaderboard() {
  const { profile } = useAuthStore();
  const [rows, setRows] = useState<LeaderboardRow[]>([]);
  const [myRank, setMyRank] = useState<number | null>(null);

  useEffect(() => {
    api.get("/leaderboard/").then(({ data }) => {
      setRows(data.results);
      setMyRank(data.my_rank);
    });
  }, []);

  const medalColor = ["text-warning-400", "text-void-200", "text-danger-400"];

  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      <div className="flex items-center gap-3">
        <Trophy className="h-7 w-7 text-warning-400" />
        <h1 className="font-display text-3xl text-void-100">Leaderboard</h1>
      </div>
      {myRank && (
        <p className="mt-2 text-void-400">
          You're currently ranked <span className="font-mono text-brand-400">#{myRank}</span>.
        </p>
      )}

      <Card className="mt-8">
        <CardContent className="divide-y divide-void-600 p-0">
          {rows.map((row, i) => (
            <div
              key={row.id}
              className={cn(
                "flex items-center justify-between px-5 py-3",
                row.id === profile?.id && "bg-brand-500/10"
              )}
            >
              <div className="flex items-center gap-4">
                <span className={cn("w-6 text-center font-mono text-sm", i < 3 ? medalColor[i] : "text-void-400")}>
                  {i < 3 ? <Medal className="h-4 w-4" /> : i + 1}
                </span>
                <span className="text-sm text-void-100">{row.display_name || row.username}</span>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <span className="text-void-400">{row.labs_completed} labs</span>
                <span className="font-mono text-success-400">{row.total_points} pts</span>
              </div>
            </div>
          ))}
          {rows.length === 0 && <p className="p-5 text-sm text-void-400">No submissions yet — be the first.</p>}
        </CardContent>
      </Card>
    </div>
  );
}
