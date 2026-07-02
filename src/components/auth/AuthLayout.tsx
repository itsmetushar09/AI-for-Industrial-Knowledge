import type { ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { APP_NAME, APP_TAGLINE } from "@/constants/api";

export function AuthLayout({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <div className="hidden lg:flex flex-col justify-between p-10 bg-gradient-to-br from-primary via-chart-5 to-chart-1 text-primary-foreground relative overflow-hidden">
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage:
              "radial-gradient(circle at 20% 30%, white 1px, transparent 1px), radial-gradient(circle at 80% 70%, white 1px, transparent 1px)",
            backgroundSize: "40px 40px",
          }}
        />
        <Link to="/login" className="relative flex items-center gap-2 z-10">
          <div className="h-10 w-10 rounded-lg bg-white/20 backdrop-blur flex items-center justify-center font-bold">
            I
          </div>
          <div>
            <div className="font-semibold">{APP_NAME}</div>
            <div className="text-xs opacity-80">{APP_TAGLINE}</div>
          </div>
        </Link>
        <div className="relative z-10 max-w-md">
          <h2 className="text-3xl font-semibold leading-tight">
            Turn industrial documents into instant answers.
          </h2>
          <p className="mt-4 text-sm opacity-90">
            Upload manuals, SOPs, inspection reports and compliance records. Ask anything. INDUS AI
            grounds every answer in your sources with full citations.
          </p>
          <div className="mt-8 flex gap-6 text-xs opacity-90">
            <div>
              <div className="text-2xl font-semibold">12k+</div>documents indexed
            </div>
            <div>
              <div className="text-2xl font-semibold">38k</div>graph nodes
            </div>
            <div>
              <div className="text-2xl font-semibold">99.8%</div>uptime
            </div>
          </div>
        </div>
        <div className="relative z-10 text-xs opacity-70">
          © 2026 INDUS AI · Industrial Intelligence
        </div>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-10 bg-background">
        <div className="w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-2 mb-8">
            <div className="h-10 w-10 rounded-lg bg-primary text-primary-foreground flex items-center justify-center font-bold">
              I
            </div>
            <div className="font-semibold">{APP_NAME}</div>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          {subtitle && <p className="text-sm text-muted-foreground mt-1.5">{subtitle}</p>}
          <div className="mt-6">{children}</div>
          {footer && <div className="mt-6 text-center text-sm text-muted-foreground">{footer}</div>}
        </div>
      </div>
    </div>
  );
}
