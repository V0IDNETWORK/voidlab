import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ShieldHalf } from "lucide-react";

export function Login() {
  const navigate = useNavigate();
  const { login, error } = useAuthStore();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await login(username, password);
      navigate("/dashboard");
    } catch {
      // error is surfaced from the store
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-md flex-col items-center px-6 py-20">
      <ShieldHalf className="mb-4 h-10 w-10 text-brand-500" />
      <Card className="w-full">
        <CardHeader>
          <CardTitle>Log in to VOIDLAB</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-void-400">Username</label>
              <Input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus required />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-void-400">Password</label>
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </div>
            {error && <p className="text-sm text-danger-400">{error}</p>}
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? "authenticating..." : "Log in"}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-void-400">
            No account? <Link to="/register" className="text-brand-400 hover:underline">Register</Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
