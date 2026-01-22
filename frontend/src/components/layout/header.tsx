"use client";

import { Navigation } from "./navigation";
import { ThemeToggle } from "@/components/theme-toggle";
import { TrendingUp } from "lucide-react";

export function Header() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/80 backdrop-blur-xl supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center">
        <div className="mr-8 flex">
          <a
            className="group flex items-center space-x-3 transition-opacity hover:opacity-80"
            href="/"
          >
            <div className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-primary/80 shadow-sm ring-1 ring-primary/20">
              <TrendingUp className="h-4 w-4 text-primary-foreground" strokeWidth={2.5} />
            </div>
            <div className="hidden flex-col sm:flex">
              <span className="font-display text-sm font-semibold tracking-tight">
                Finance
              </span>
              <span className="text-[10px] font-medium text-muted-foreground tracking-wide">
                DASHBOARD
              </span>
            </div>
          </a>
        </div>
        <div className="flex flex-1 items-center justify-between space-x-4">
          <Navigation />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}