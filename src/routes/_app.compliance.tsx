import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Download, CheckCircle2, Clock, AlertCircle, AlertTriangle } from "lucide-react";
import { api } from "@/services/api";
import { PageHeader } from "@/components/layout/AppShell";
import { StatCard } from "@/components/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
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

export const Route = createFileRoute("/_app/compliance")({
  component: CompliancePage,
});

function CompliancePage() {
  const { data = [] } = useQuery({ queryKey: ["compliance"], queryFn: api.compliance });

  const counts = {
    Passed: data.filter((c) => c.status === "Passed").length,
    Pending: data.filter((c) => c.status === "Pending").length,
    Critical: data.filter((c) => c.status === "Critical").length,
    Expired: data.filter((c) => c.status === "Expired").length,
  };

  return (
    <div>
      <PageHeader
        title="Compliance"
        description="Audit posture, regulatory references and certifications."
        actions={
          <Button className="gap-2">
            <Download className="h-4 w-4" /> Export PDF Report
          </Button>
        }
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Passed"
          value={counts.Passed}
          icon={<CheckCircle2 className="h-5 w-5" />}
          tone="success"
        />
        <StatCard
          label="Pending"
          value={counts.Pending}
          icon={<Clock className="h-5 w-5" />}
          tone="warning"
        />
        <StatCard
          label="Critical"
          value={counts.Critical}
          icon={<AlertTriangle className="h-5 w-5" />}
          tone="destructive"
        />
        <StatCard
          label="Expired"
          value={counts.Expired}
          icon={<AlertCircle className="h-5 w-5" />}
          tone="destructive"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Compliance Checklist</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Item</TableHead>
                  <TableHead>Regulation</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last Audit</TableHead>
                  <TableHead>Owner</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell className="font-medium">{c.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{c.regulation}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge
                        className={cn(
                          c.status === "Passed" && "bg-success text-success-foreground",
                          c.status === "Pending" && "bg-warning text-warning-foreground",
                          (c.status === "Critical" || c.status === "Expired") &&
                            "bg-destructive text-destructive-foreground",
                        )}
                      >
                        {c.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{c.lastAudit}</TableCell>
                    <TableCell>{c.owner}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Audit Timeline</CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="space-y-4">
              {data.map((c, i) => (
                <li key={c.id} className="relative pl-6">
                  <span
                    className={cn(
                      "absolute left-0 top-1 h-3 w-3 rounded-full",
                      c.status === "Passed"
                        ? "bg-success"
                        : c.status === "Pending"
                          ? "bg-warning"
                          : "bg-destructive",
                    )}
                  />
                  {i < data.length - 1 && (
                    <span className="absolute left-[5px] top-4 bottom-[-1rem] w-px bg-border" />
                  )}
                  <p className="text-sm font-medium">{c.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {c.lastAudit} · {c.regulation}
                  </p>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
