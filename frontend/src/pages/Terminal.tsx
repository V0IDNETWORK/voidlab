import { useEffect, useRef, useState } from "react";
import { useLabStore } from "@/store/labStore";
import { tokenStore, WS_BASE_URL } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { TerminalSquare, Circle } from "lucide-react";

interface Line {
  text: string;
  kind: "output" | "input";
}

export function TerminalPage() {
  const { labs, fetchAll } = useLabStore();
  const [labSlug, setLabSlug] = useState<string>("");
  const [lines, setLines] = useState<Line[]>([]);
  const [command, setCommand] = useState("");
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  useEffect(() => {
    if (!labSlug && labs.length > 0) setLabSlug(labs[0].slug);
  }, [labs, labSlug]);

  useEffect(() => {
    if (!labSlug) return;
    const token = tokenStore.getAccess();
    const ws = new WebSocket(`${WS_BASE_URL}/ws/terminal/${labSlug}/?token=${token}`);
    wsRef.current = ws;
    setLines([]);

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.type === "clear") setLines([]);
      else setLines((prev) => [...prev, { text: payload.text, kind: "output" }]);
    };

    return () => ws.close();
  }, [labSlug]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  function sendCommand(e: React.FormEvent) {
    e.preventDefault();
    if (!command.trim() || !wsRef.current) return;
    setLines((prev) => [...prev, { text: command, kind: "input" }]);
    wsRef.current.send(command);
    setCommand("");
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      <div className="flex items-center gap-3">
        <TerminalSquare className="h-7 w-7 text-brand-500" />
        <h1 className="font-display text-3xl text-void-100">Sandboxed Terminal</h1>
      </div>
      <p className="mt-2 text-void-400">
        Runs against an isolated, non-privileged container with an allowlisted recon toolkit —
        not a general-purpose shell.
      </p>

      <div className="mt-6 flex items-center gap-3">
        <select
          value={labSlug}
          onChange={(e) => setLabSlug(e.target.value)}
          className="rounded-md border border-void-600 bg-void-900 px-3 py-2 text-sm text-void-100"
        >
          {labs.map((lab) => (
            <option key={lab.slug} value={lab.slug}>{lab.category.code} · {lab.title}</option>
          ))}
        </select>
        <span className="flex items-center gap-1.5 text-xs text-void-400">
          <Circle className={`h-2 w-2 fill-current ${connected ? "text-success-500" : "text-danger-500"}`} />
          {connected ? "connected" : "disconnected"}
        </span>
      </div>

      <Card className="mt-6">
        <CardContent className="p-0">
          <div className="h-96 overflow-y-auto p-4 font-mono text-sm">
            {lines.map((line, i) => (
              <p key={i} className={line.kind === "input" ? "text-brand-400" : "whitespace-pre-wrap text-void-200"}>
                {line.kind === "input" ? `$ ${line.text}` : line.text}
              </p>
            ))}
            <div ref={bottomRef} />
          </div>
          <form onSubmit={sendCommand} className="flex items-center gap-2 border-t border-void-600 p-3">
            <span className="font-mono text-brand-400">$</span>
            <Input
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              placeholder="curl, nmap, dig, whoami, help..."
              className="border-none bg-transparent font-mono focus:ring-0"
            />
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
