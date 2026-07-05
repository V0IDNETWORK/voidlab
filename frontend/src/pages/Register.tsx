import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ShieldHalf } from "lucide-react";

export function Register() {
  const navigate = useNavigate();
  const { register, error } = useAuthStore();
  const [form, setForm] = useState({
    username: "", email: "", display_name: "", password: "", password_confirm: "",
  });
  const [submitting, setSubmitting] = useState(false);

  function update(field: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement>) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await register(form);
      navigate("/dashboard");
    } catch {
      // error surfaced from the store
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-md flex-col items-center px-6 py-20">
      <ShieldHalf className="mb-4 h-10 w-10 text-brand-500" />
      <Card className="w-full">
        <CardHeader>
          <CardTitle>Create your VOIDLAB account</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-void-400">Username</label>
              <Input value={form.username} onChange={update("username")} required />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-void-400">Display name</label>
              <Input value={form.display_name} onChange={update("display_name")} placeholder="shown on the leaderboard" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-void-400">Email</label>
              <Input type="email" value={form.email} onChange={update("email")} required />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-void-400">Password</label>
              <Input type="password" value={form.password} onChange={update("password")} required minLength={10} />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-void-400">Confirm password</label>
              <Input type="password" value={form.password_confirm} onChange={update("password_confirm")} required />
            </div>
            {error && <p className="text-sm text-danger-400">{error}</p>}
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? "creating account..." : "Create account"}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-void-400">
            Already registered? <Link to="/login" className="text-brand-400 hover:underline">Log in</Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
