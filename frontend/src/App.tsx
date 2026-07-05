import { useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import { Navbar } from "@/components/layout/Navbar";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";

import { Landing } from "@/pages/Landing";
import { Login } from "@/pages/Login";
import { Register } from "@/pages/Register";
import { Dashboard } from "@/pages/Dashboard";
import { Labs } from "@/pages/Labs";
import { LabDetail } from "@/pages/LabDetail";
import { Leaderboard } from "@/pages/Leaderboard";
import { TerminalPage } from "@/pages/Terminal";
import { NotFound } from "@/pages/NotFound";

export default function App() {
  const hydrate = useAuthStore((s) => s.hydrate);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  return (
    <div className="min-h-screen">
      <Navbar />
      <main>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/labs" element={<Labs />} />
            <Route path="/labs/:slug" element={<LabDetail />} />
            <Route path="/leaderboard" element={<Leaderboard />} />
            <Route path="/terminal" element={<TerminalPage />} />
          </Route>

          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </div>
  );
}
