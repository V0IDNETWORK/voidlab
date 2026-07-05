import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

export function NotFound() {
  return (
    <div className="mx-auto flex max-w-lg flex-col items-center px-6 py-32 text-center">
      <p className="font-mono text-6xl text-brand-500">404</p>
      <h1 className="mt-4 font-display text-2xl text-void-100">Target not found</h1>
      <p className="mt-2 text-void-400">This route doesn't exist in the range.</p>
      <Button className="mt-6" asChild>
        <Link to="/">Return to base</Link>
      </Button>
    </div>
  );
}
