import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function StatCard({
  label,
  value,
  icon,
  trend,
  tone = "default",
}: {
  label: string;
  value: string | number;
  icon: ReactNode;
  trend?: string;
  tone?: "default" | "success" | "warning" | "destructive";
}) {
  const toneCls = {
    default: "from-primary/10 to-primary/5 text-primary",
    success: "from-success/10 to-success/5 text-success",
    warning: "from-warning/15 to-warning/5 text-warning",
    destructive: "from-destructive/10 to-destructive/5 text-destructive",
  }[tone];

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <Card className="hover:shadow-md transition-shadow">
        <CardContent className="p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-xs uppercase tracking-wider text-muted-foreground">{label}</p>
              <p className="text-2xl font-semibold tracking-tight mt-1.5">{value}</p>
              {trend && <p className="text-xs text-muted-foreground mt-1.5">{trend}</p>}
            </div>
            <div
              className={cn(
                "h-10 w-10 rounded-lg bg-gradient-to-br flex items-center justify-center shrink-0",
                toneCls,
              )}
            >
              {icon}
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
