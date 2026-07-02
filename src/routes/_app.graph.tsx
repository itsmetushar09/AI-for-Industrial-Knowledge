import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Search, ZoomIn, ZoomOut } from "lucide-react";
import { api } from "@/services/api";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export const Route = createFileRoute("/_app/graph")({
  component: GraphPage,
});

const TYPE_COLORS: Record<string, string> = {
  Machine: "var(--chart-1)",
  Department: "var(--chart-2)",
  Procedure: "var(--chart-3)",
  Person: "var(--chart-5)",
  Regulation: "var(--chart-4)",
  Failure: "var(--destructive)",
  Task: "var(--warning)",
};

function GraphPage() {
  const { data } = useQuery({ queryKey: ["graph"], queryFn: api.graph });
  const [zoom, setZoom] = useState(1);
  const [query, setQuery] = useState("");

  const nodes = (data?.nodes ?? []).filter(
    (n) => !query || n.label.toLowerCase().includes(query.toLowerCase()),
  );
  const visibleIds = new Set(nodes.map((n) => n.id));
  const edges = (data?.edges ?? []).filter((e) => visibleIds.has(e.from) && visibleIds.has(e.to));

  return (
    <div>
      <PageHeader
        title="Knowledge Graph"
        description="Explore relationships across machines, procedures, people and regulations."
      />

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-4">
        <Card>
          <CardContent className="p-3">
            <div className="flex items-center gap-2 mb-3">
              <div className="relative flex-1">
                <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search nodes…"
                  className="pl-9"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </div>
              <Button
                variant="outline"
                size="icon"
                onClick={() => setZoom((z) => Math.max(0.5, z - 0.2))}
              >
                <ZoomOut className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                onClick={() => setZoom((z) => Math.min(2, z + 0.2))}
              >
                <ZoomIn className="h-4 w-4" />
              </Button>
            </div>

            <div className="rounded-lg border bg-muted/20 overflow-hidden">
              <svg viewBox="0 0 800 600" className="w-full h-[520px]">
                <g style={{ transform: `scale(${zoom})`, transformOrigin: "center" }}>
                  {edges.map((e, i) => {
                    const a = data!.nodes.find((n) => n.id === e.from)!;
                    const b = data!.nodes.find((n) => n.id === e.to)!;
                    return (
                      <g key={i}>
                        <line
                          x1={a.x}
                          y1={a.y}
                          x2={b.x}
                          y2={b.y}
                          stroke="var(--border)"
                          strokeWidth={1.5}
                        />
                        <text
                          x={(a.x + b.x) / 2}
                          y={(a.y + b.y) / 2}
                          fontSize="9"
                          fill="var(--muted-foreground)"
                          textAnchor="middle"
                        >
                          {e.label}
                        </text>
                      </g>
                    );
                  })}
                  {nodes.map((n) => (
                    <g key={n.id} className="cursor-pointer">
                      <circle
                        cx={n.x}
                        cy={n.y}
                        r={26}
                        fill={TYPE_COLORS[n.type]}
                        fillOpacity={0.15}
                        stroke={TYPE_COLORS[n.type]}
                        strokeWidth={2}
                      />
                      <text
                        x={n.x}
                        y={n.y + 4}
                        fontSize="11"
                        fill="var(--foreground)"
                        textAnchor="middle"
                        fontWeight="500"
                      >
                        {n.label}
                      </text>
                    </g>
                  ))}
                </g>
              </svg>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <h3 className="font-semibold mb-3">Node Types</h3>
            <div className="space-y-2">
              {Object.entries(TYPE_COLORS).map(([type, color]) => (
                <div key={type} className="flex items-center gap-2 text-sm">
                  <span className="h-3 w-3 rounded-full" style={{ background: color }} />
                  {type}
                </div>
              ))}
            </div>
            <div className="mt-5 pt-4 border-t">
              <h3 className="font-semibold mb-2">Edge Types</h3>
              <div className="flex flex-wrap gap-1.5">
                {["Depends On", "Related To", "Owned By", "Referenced In"].map((e) => (
                  <Badge key={e} variant="outline">
                    {e}
                  </Badge>
                ))}
              </div>
            </div>
            <div className="mt-5 pt-4 border-t text-xs text-muted-foreground">
              Showing <span className="font-semibold text-foreground">{nodes.length}</span> of{" "}
              {data?.nodes.length ?? 0} nodes
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
