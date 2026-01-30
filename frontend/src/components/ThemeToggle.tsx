import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export type ThemeToggleVariant = "icon" | "pill";

interface ThemeToggleProps {
  className?: string;
  /** "pill" = segmented control (Light | Dark), "icon" = single icon */
  variant?: ThemeToggleVariant;
  size?: "default" | "sm" | "icon";
}

export function ThemeToggle({
  className,
  variant = "pill",
  size = "default",
}: ThemeToggleProps) {
  const { setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return (
      <div
        className={cn(
          "rounded-full bg-muted/50 animate-pulse",
          variant === "pill" ? "h-9 w-20" : "h-9 w-9"
        )}
      />
    );
  }

  const isDark = resolvedTheme === "dark";
  const label = isDark ? "Switch to light mode" : "Switch to dark mode";

  if (variant === "pill") {
    return (
      <div
        role="group"
        aria-label="Theme"
        className={cn(
          "inline-flex p-0.5 rounded-full border border-border",
          "bg-muted/50 dark:bg-muted/60 shadow-sm",
          "ring-1 ring-black/[0.04] dark:ring-white/5",
          className
        )}
      >
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              aria-pressed={!isDark}
              aria-label="Light mode"
              onClick={() => setTheme("light")}
              className={cn(
                "inline-flex items-center justify-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-all duration-200",
                !isDark
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Sun className="h-3.5 w-3.5" />
              <span>Light</span>
            </button>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="font-mono text-xs">
            Light mode
          </TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              aria-pressed={isDark}
              aria-label="Dark mode"
              onClick={() => setTheme("dark")}
              className={cn(
                "inline-flex items-center justify-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-all duration-200",
                isDark
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Moon className="h-3.5 w-3.5" />
              <span>Dark</span>
            </button>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="font-mono text-xs">
            Dark mode
          </TooltipContent>
        </Tooltip>
      </div>
    );
  }

  const trigger = (
    <Button
      variant="ghost"
      size={size}
      aria-label={label}
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className={cn(
        "relative rounded-full text-muted-foreground hover:text-foreground",
        "hover:bg-sidebar-accent transition-all duration-200",
        "ring-1 ring-transparent hover:ring-border focus-visible:ring-ring",
        className
      )}
    >
      <span className="relative inline-flex h-4 w-4 shrink-0 items-center justify-center">
        <Sun
          className={cn(
            "h-4 w-4 transition-all duration-200 absolute",
            isDark ? "scale-0 opacity-0" : "scale-100 opacity-100"
          )}
        />
        <Moon
          className={cn(
            "h-4 w-4 transition-all duration-200 absolute",
            isDark ? "scale-100 opacity-100" : "scale-0 opacity-0"
          )}
        />
      </span>
    </Button>
  );

  return (
    <Tooltip>
      <TooltipTrigger asChild>{trigger}</TooltipTrigger>
      <TooltipContent side="bottom" className="font-mono text-xs">
        {label}
      </TooltipContent>
    </Tooltip>
  );
}
