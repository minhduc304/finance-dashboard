"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  TrendingUp,
  PieChart,
  Users,
  BarChart3,
  Home,
  MessageSquare
} from "lucide-react";

const navigation = [
  {
    name: "Dashboard",
    href: "/",
    icon: Home,
  },
  {
    name: "Market",
    href: "/market",
    icon: TrendingUp,
  },
  {
    name: "Sentiment",
    href: "/sentiment",
    icon: MessageSquare,
  },
  {
    name: "Portfolio",
    href: "/portfolio",
    icon: PieChart,
  },
  {
    name: "Insiders",
    href: "/insiders",
    icon: Users,
  },
  {
    name: "Analytics",
    href: "/analytics",
    icon: BarChart3,
  },
];

export function Navigation() {
  const pathname = usePathname();

  return (
    <nav className="hidden md:flex items-center space-x-1">
      {navigation.map((item) => {
        const Icon = item.icon;
        const isActive = pathname === item.href;
        return (
          <Link
            key={item.name}
            href={item.href}
            className={cn(
              "relative flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all",
              "hover:bg-accent/50",
              isActive
                ? "text-foreground"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <Icon className="h-4 w-4" strokeWidth={2} />
            <span>{item.name}</span>
            {isActive && (
              <div className="absolute bottom-0 left-1/2 -translate-x-1/2 h-0.5 w-8 bg-primary rounded-full" />
            )}
          </Link>
        );
      })}
    </nav>
  );
}