import { createFileRoute } from "@tanstack/react-router";
import { Plus } from "lucide-react";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export const Route = createFileRoute("/_app/users")({
  component: UsersPage,
});

const USERS = [
  {
    name: "Arjun Mehta",
    email: "arjun@indus.ai",
    role: "Plant Manager",
    dept: "Operations",
    status: "Active",
  },
  {
    name: "Priya Rao",
    email: "priya@indus.ai",
    role: "Safety Officer",
    dept: "Safety",
    status: "Active",
  },
  {
    name: "Rahul Khanna",
    email: "rahul@indus.ai",
    role: "Maintenance Engineer",
    dept: "Maintenance",
    status: "Active",
  },
  {
    name: "Neha Singh",
    email: "neha@indus.ai",
    role: "Administrator",
    dept: "IT",
    status: "Active",
  },
  {
    name: "Vikram Iyer",
    email: "vikram@indus.ai",
    role: "Operator",
    dept: "Operations",
    status: "Invited",
  },
];

function UsersPage() {
  return (
    <div>
      <PageHeader
        title="Users & Roles"
        description="Manage access to your knowledge platform."
        actions={
          <Button className="gap-2">
            <Plus className="h-4 w-4" /> Invite User
          </Button>
        }
      />

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {USERS.map((u) => (
                <TableRow key={u.email}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <Avatar className="h-8 w-8">
                        <AvatarFallback className="bg-primary text-primary-foreground text-xs">
                          {u.name
                            .split(" ")
                            .map((p) => p[0])
                            .join("")}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <div className="font-medium">{u.name}</div>
                        <div className="text-xs text-muted-foreground">{u.email}</div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary">{u.role}</Badge>
                  </TableCell>
                  <TableCell>{u.dept}</TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={u.status === "Active" ? "border-success text-success" : ""}
                    >
                      {u.status}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
