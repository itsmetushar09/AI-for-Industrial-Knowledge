import { Link, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard,
  MessageSquareText,
  FileText,
  Network,
  Building2,
  ShieldCheck,
  Wrench,
  BarChart3,
  Users,
  Settings,
  HelpCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { APP_NAME } from "@/constants/api";

const items = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/copilot", label: "AI Copilot", icon: MessageSquareText },
  { to: "/documents", label: "Documents", icon: FileText },
  { to: "/graph", label: "Knowledge Graph", icon: Network },
  { to: "/departments", label: "Departments", icon: Building2 },
  { to: "/compliance", label: "Compliance", icon: ShieldCheck },
  { to: "/maintenance", label: "Maintenance", icon: Wrench },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/users", label: "Users", icon: Users },
  { to: "/settings", label: "Settings", icon: Settings },
  { to: "/help", label: "Help", icon: HelpCircle },
] as const;

export function Sidebar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <aside className="hidden md:flex flex-col w-64 shrink-0 border-r border-sidebar-border bg-sidebar text-sidebar-foreground">
      <div className="h-16 px-5 flex items-center gap-2 border-b border-sidebar-border">
        <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-primary to-chart-5 flex items-center justify-center text-primary-foreground font-bold shadow-sm">
          I
        </div>
        <div className="flex flex-col leading-tight">
          <span className="font-semibold tracking-tight">{APP_NAME}</span>
          <span className="text-[10px] uppercase text-muted-foreground tracking-wider">
            Industrial Intelligence
          </span>
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto py-3 px-3 space-y-0.5">
        {items.map((it) => {
          const active =
            pathname === it.to || (it.to !== "/dashboard" && pathname.startsWith(it.to));
          const Icon = it.icon;
          return (
            <Link
              key={it.to}
              to={it.to}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                  : "text-sidebar-foreground/80 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              <span>{it.label}</span>
              {active && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-primary" />}
            </Link>
          );
        })}
      </nav>
      <div className="p-3 border-t border-sidebar-border">
        <div className="rounded-lg bg-gradient-to-br from-primary/10 to-chart-5/10 p-3 text-xs">
          <div className="font-medium text-foreground">Knowledge Coverage</div>
          <div className="mt-1 text-muted-foreground">78% of plant assets indexed</div>
          <div className="mt-2 h-1.5 rounded-full bg-muted overflow-hidden">
            <div className="h-full w-[78%] bg-primary" />
          </div>
        </div>
      </div>
    </aside>
  );
}
