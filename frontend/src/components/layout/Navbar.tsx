import { Link, NavLink, useNavigate } from "react-router-dom";
import { Terminal, Trophy, LayoutGrid, LogOut, ShieldHalf } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { Button } from "@/components/ui/button";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-1.5 text-sm font-medium transition-colors ${
    isActive ? "text-brand-400" : "text-void-400 hover:text-void-100"
  }`;

export function Navbar() {
  const { profile, isAuthenticated, logout } = useAuthStore();
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-40 border-b border-void-600 bg-void-900/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
        <Link to="/" className="flex items-center gap-2 font-display text-lg text-void-100">
          <ShieldHalf className="h-5 w-5 text-brand-500" />
          VOID<span className="text-brand-500">LAB</span>
        </Link>

        {isAuthenticated && (
          <nav className="hidden items-center gap-6 md:flex">
            <NavLink to="/labs" className={navLinkClass}>
              <LayoutGrid className="h-4 w-4" /> Labs
            </NavLink>
            <NavLink to="/leaderboard" className={navLinkClass}>
              <Trophy className="h-4 w-4" /> Leaderboard
            </NavLink>
            <NavLink to="/terminal" className={navLinkClass}>
              <Terminal className="h-4 w-4" /> Terminal
            </NavLink>
          </nav>
        )}

        <div className="flex items-center gap-3">
          {isAuthenticated && profile ? (
            <>
              <div className="hidden text-right sm:block">
                <p className="text-sm font-medium text-void-100">{profile.display_name || profile.username}</p>
                <p className="font-mono text-xs text-success-400">{profile.total_points} pts</p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  logout();
                  navigate("/login");
                }}
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" size="sm" onClick={() => navigate("/login")}>
                Log in
              </Button>
              <Button size="sm" onClick={() => navigate("/register")}>
                Get started
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
