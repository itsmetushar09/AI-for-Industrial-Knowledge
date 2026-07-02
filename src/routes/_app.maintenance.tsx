import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Wrench, Sparkles, AlertTriangle } from "lucide-react";
import { api } from "@/services/api";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_app/maintenance")({
  component: MaintenancePage,
});

const EQUIPMENT = [
  "Pump A",
  "Boiler 4",
  "Compressor C12",
  "Turbine T2",
  "Conveyor B3",
  "Cooling Tower",
];

function MaintenancePage() {
  const { data = [] } = useQuery({ queryKey: ["maintenance"], queryFn: api.maintenance });

  return (
    <div>
      <PageHeader
        title="Maintenance"
        description="Tasks, equipment health and AI recommendations."
      />

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Equipment</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            {EQUIPMENT.map((e) => (
              <button
                key={e}
                className="w-full text-left text-sm px-3 py-2 rounded-md hover:bg-muted flex items-center gap-2"
              >
                <Wrench className="h-3.5 w-3.5 text-muted-foreground" /> {e}
              </button>
            ))}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Upcoming Tasks</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Equipment</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Due</TableHead>
                    <TableHead>Priority</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Assignee</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.map((t) => (
                    <TableRow key={t.id}>
                      <TableCell className="font-medium">{t.equipment}</TableCell>
                      <TableCell>{t.type}</TableCell>
                      <TableCell className="text-muted-foreground">{t.due}</TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={cn(
                            t.priority === "Critical" && "border-destructive text-destructive",
                            t.priority === "High" && "border-warning text-warning",
                          )}
                        >
                          {t.priority}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          className={cn(
                            t.status === "Done" && "bg-success text-success-foreground",
                            t.status === "Open" && "bg-muted text-foreground",
                            t.status === "In Progress" && "bg-primary text-primary-foreground",
                            t.status === "Overdue" && "bg-destructive text-destructive-foreground",
                          )}
                        >
                          {t.status}
                        </Badge>
                      </TableCell>
                      <TableCell>{t.assignee}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="flex flex-row items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" />
                <CardTitle className="text-base">AI Recommendations</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="rounded-lg border p-3">
                  <p className="font-medium">Replace Pump A bearing assembly</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Vibration data + 3 similar past failures suggest replacement within 7 days.
                  </p>
                </div>
                <div className="rounded-lg border p-3">
                  <p className="font-medium">Recalibrate Compressor C12 sensors</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Drift detected since last calibration cycle (97 days ago).
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-warning" />
                <CardTitle className="text-base">Failure Timeline</CardTitle>
              </CardHeader>
              <CardContent>
                <ol className="space-y-3 text-sm">
                  {[
                    { d: "Jun 24", t: "Pump A — bearing seizure" },
                    { d: "May 18", t: "Conveyor B3 — motor overheat" },
                    { d: "Apr 02", t: "Boiler 4 — pressure spike (resolved)" },
                  ].map((e) => (
                    <li key={e.d} className="flex gap-3">
                      <span className="text-xs text-muted-foreground w-14 shrink-0 mt-0.5">
                        {e.d}
                      </span>
                      <span>{e.t}</span>
                    </li>
                  ))}
                </ol>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
