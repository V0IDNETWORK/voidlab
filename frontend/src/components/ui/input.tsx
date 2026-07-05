import React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "w-full rounded-md border border-void-600 bg-void-900 px-3 py-2 text-sm text-void-100 placeholder:text-void-400",
        "focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-500",
        className
      )}
      {...props}
    />
  )
);
Input.displayName = "Input";
