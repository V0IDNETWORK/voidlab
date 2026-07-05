import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  LockOpen, Settings, Package, KeyRound, Terminal as TerminalIcon,
  DraftingCompass, Fingerprint, ShieldAlert, FileWarning, AlertTriangle,
} from "lucide-react";

const BOOT_LINES = [
  "voidlab@core:~$ initializing training range...",
  "[ OK ] postgres    reachable",
  "[ OK ] redis        reachable",
  "[ OK ] attacker-box  sandboxed, allowlist active",
  "[ OK ] 5 live vulnerable targets online",
  "[ OK ] OWASP Top 10:2025 curriculum loaded",
  "voidlab@core:~$ ready. good luck.",
];

const CATEGORIES = [
  { code: "A01", name: "Broken Access Control", icon: LockOpen },
  { code: "A02", name: "Security Misconfiguration", icon: Settings },
  { code: "A03", name: "Software Supply Chain Failures", icon: Package },
  { code: "A04", name: "Cryptographic Failures", icon: KeyRound },
  { code: "A05", name: "Injection", icon: TerminalIcon },
  { code: "A06", name: "Insecure Design", icon: DraftingCompass },
  { code: "A07", name: "Authentication Failures", icon: Fingerprint },
  { code: "A08", name: "Software/Data Integrity Failures", icon: ShieldAlert },
  { code: "A09", name: "Security Logging & Alerting Failures", icon: FileWarning },
  { code: "A10", name: "Mishandling of Exceptional Conditions", icon: AlertTriangle },
];

function BootSequence() {
  const [visibleLines, setVisibleLines] = useState(0);

  useEffect(() => {
    if (visibleLines >= BOOT_LINES.length) return;
    const t = setTimeout(() => setVisibleLines((n) => n + 1), 260);
    return () => clearTimeout(t);
  }, [visibleLines]);

  return (
    <div className="glass-panel relative overflow-hidden rounded-lg p-5 font-mono text-sm">
      <div className="absolute inset-0 overflow-hidden opacity-20">
        <div className="animate-scanline h-1/3 w-full bg-gradient-to-b from-transparent via-brand-500 to-transparent" />
      </div>
      {BOOT_LINES.slice(0, visibleLines).map((line, i) => (
        <p key={i} className={line.includes("[ OK ]") ? "text-success-400" : "text-void-200"}>
          {line}
        </p>
      ))}
      <span className="inline-block h-4 w-2 animate-pulse bg-brand-500 align-middle" />
    </div>
  );
}

export function Landing() {
  return (
    <div className="mx-auto max-w-7xl px-6 py-16">
      <section className="grid items-center gap-12 lg:grid-cols-2">
        <div>
          <p className="mb-3 font-mono text-sm uppercase tracking-[0.3em] text-brand-400">
            ∆ Join VOID ∆ — by V0IDNETWORK
          </p>
          <h1 className="font-display text-4xl font-semibold leading-tight text-void-100 sm:text-5xl">
            Break things safely.
            <br />
            <span className="text-brand-500">Learn the OWASP Top 10:2025</span> by exploiting it.
          </h1>
          <p className="mt-5 max-w-xl text-void-400">
            VOIDLAB is a self-hosted, containerized penetration testing range: live vulnerable
            targets, an in-browser sandboxed terminal, flag-based scoring, and structured labs
            across every current OWASP risk category — from Broken Access Control to the
            brand-new Mishandling of Exceptional Conditions.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button size="lg" asChild>
              <Link to="/register">Start hacking →</Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link to="/login">I have an account</Link>
            </Button>
          </div>
        </div>
        <BootSequence />
      </section>

      <section className="mt-24">
        <h2 className="font-display text-2xl text-void-100">OWASP Top 10:2025 coverage</h2>
        <p className="mt-2 max-w-2xl text-void-400">
          OWASP refreshed the Top 10 in late 2025 — SSRF and IDOR now live under Broken Access
          Control, and a brand-new category, Mishandling of Exceptional Conditions, replaced the
          old standalone SSRF slot. VOIDLAB's curriculum tracks that current list.
        </p>
        <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {CATEGORIES.map(({ code, name, icon: Icon }) => (
            <Card key={code} className="group transition-colors hover:border-brand-500/60">
              <CardContent className="flex flex-col items-start gap-3">
                <div className="rounded-md bg-brand-500/10 p-2 text-brand-400 group-hover:bg-brand-500/20">
                  <Icon className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-mono text-xs text-void-400">{code}</p>
                  <p className="text-sm font-medium text-void-100">{name}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className="mt-24 grid gap-6 sm:grid-cols-3">
        {[
          { title: "Live isolated targets", body: "Every injection/access-control lab runs against a real, disposable, non-privileged container — not a quiz." },
          { title: "Sandboxed terminal", body: "An in-browser WebSocket terminal proxies an allowlisted recon toolkit into the lab network, enforced server-side twice over." },
          { title: "Points, hints, leaderboard", body: "Capture flags for points, spend points to unlock hints, and climb a live leaderboard against other operatives." },
        ].map((f) => (
          <Card key={f.title}>
            <CardContent>
              <h3 className="font-display text-void-100">{f.title}</h3>
              <p className="mt-2 text-sm text-void-400">{f.body}</p>
            </CardContent>
          </Card>
        ))}
      </section>
    </div>
  );
}
