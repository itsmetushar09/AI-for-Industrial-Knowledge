import { createFileRoute } from "@tanstack/react-router";
import { Building2, Users } from "lucide-react";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent } from "@/components/ui/card";

export const Route = createFileRoute("/_app/departments")({
  component: DepartmentsPage,
});

const DEPTS = [
  { name: "Maintenance", lead: "Rahul Khanna", docs: 3240, members: 48 },
  { name: "Safety", lead: "Priya Rao", docs: 2180, members: 22 },
  { name: "Operations", lead: "Arjun Mehta", docs: 2890, members: 76 },
  { name: "Quality", lead: "Neha Singh", docs: 1450, members: 18 },
  { name: "Compliance", lead: "Vikram Iyer", docs: 980, members: 12 },
  { name: "Engineering", lead: "Sara Khan", docs: 1740, members: 34 },
];

function DepartmentsPage() {
  return (
    <div>
      <PageHeader title="Departments" description="Knowledge ownership across your organization." />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {DEPTS.map((d) => (
          <Card key={d.name} className="hover:shadow-md transition-shadow">
            <CardContent className="p-5">
              <div className="flex items-start justify-between">
                <div className="h-10 w-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                  <Building2 className="h-5 w-5" />
                </div>
                <span className="text-xs text-muted-foreground flex items-center gap-1">
                  <Users className="h-3 w-3" />
                  {d.members}
                </span>
              </div>
              <h3 className="mt-3 font-semibold">{d.name}</h3>
              <p className="text-xs text-muted-foreground">Lead: {d.lead}</p>
              <div className="mt-4 flex items-baseline gap-1">
                <span className="text-2xl font-semibold">{d.docs.toLocaleString()}</span>
                <span className="text-xs text-muted-foreground">documents</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
