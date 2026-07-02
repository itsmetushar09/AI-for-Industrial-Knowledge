import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Shield, Briefcase, Wrench, HardHat, User } from "lucide-react";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "@/lib/utils";
import type { Role } from "@/types";

export const Route = createFileRoute("/role-select")({
  component: RolePage,
});

const ROLES: { role: Role; desc: string; icon: typeof Shield }[] = [
  { role: "Administrator", desc: "Full platform & user management", icon: Shield },
  { role: "Plant Manager", desc: "Oversee operations & analytics", icon: Briefcase },
  { role: "Maintenance Engineer", desc: "Equipment & maintenance workflows", icon: Wrench },
  { role: "Safety Officer", desc: "Compliance & safety oversight", icon: HardHat },
  { role: "Operator", desc: "Daily operations & quick lookups", icon: User },
];

function RolePage() {
  const navigate = useNavigate();
  const { setRole } = useAuth();
  const [selected, setSelected] = useState<Role>("Plant Manager");
  return (
    <AuthLayout title="Choose your role" subtitle="We'll tailor your workspace accordingly">
      <div className="space-y-2">
        {ROLES.map(({ role, desc, icon: Icon }) => (
          <button
            key={role}
            onClick={() => setSelected(role)}
            className={cn(
              "w-full flex items-center gap-3 rounded-lg border p-3 text-left transition",
              selected === role ? "border-primary bg-primary/5" : "hover:bg-muted/40",
            )}
          >
            <div
              className={cn(
                "h-9 w-9 rounded-md flex items-center justify-center",
                selected === role
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium">{role}</p>
              <p className="text-xs text-muted-foreground">{desc}</p>
            </div>
          </button>
        ))}
      </div>
      <Button
        className="w-full mt-6"
        onClick={() => {
          setRole(selected);
          navigate({ to: "/dashboard" });
        }}
      >
        Continue
      </Button>
    </AuthLayout>
  );
}
