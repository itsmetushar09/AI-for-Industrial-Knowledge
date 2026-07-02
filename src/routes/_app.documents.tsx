import { createFileRoute } from "@tanstack/react-router";
import { useState, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Upload,
  Search,
  Filter,
  Download,
  Eye,
  Trash2,
  FileText,
  FileSpreadsheet,
  FileImage,
  FileType,
} from "lucide-react";
import { toast } from "sonner";
import { api } from "@/services/api";
import { PageHeader } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_app/documents")({
  component: DocumentsPage,
});

const ICONS = {
  PDF: FileText,
  DOCX: FileType,
  XLSX: FileSpreadsheet,
  CSV: FileSpreadsheet,
  TXT: FileText,
  Image: FileImage,
};

function DocumentsPage() {
  const { data: docs = [] } = useQuery({ queryKey: ["documents"], queryFn: api.documents });
  const [query, setQuery] = useState("");
  const [dept, setDept] = useState("all");
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();
  const [uploading, setUploading] = useState(false);

  const filtered = docs.filter(
    (d) =>
      (dept === "all" || d.department === dept) &&
      (!query || d.name.toLowerCase().includes(query.toLowerCase())),
  );

  const onFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    try {
      const result = await api.upload(Array.from(files));
      toast.success(`${result.queued} file(s) queued for processing`);
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div>
      <PageHeader
        title="Documents"
        description="Upload, index and govern your industrial knowledge sources."
        actions={
          <Button className="gap-2" disabled={uploading} onClick={() => inputRef.current?.click()}>
            <Upload className="h-4 w-4" /> Upload Documents
          </Button>
        }
      />

      <input
        ref={inputRef}
        type="file"
        multiple
        accept="application/pdf,.pdf"
        className="hidden"
        onChange={(e) => void onFiles(e.target.files)}
      />

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          void onFiles(e.dataTransfer.files);
        }}
        className={cn(
          "border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer mb-5",
          dragOver ? "border-primary bg-primary/5" : "border-border bg-muted/20 hover:bg-muted/30",
        )}
        onClick={() => inputRef.current?.click()}
      >
        <Upload className="h-8 w-8 mx-auto text-muted-foreground" />
        <p className="mt-2 text-sm font-medium">Drop files here or click to browse</p>
        <p className="text-xs text-muted-foreground mt-1">
          PDF, DOCX, TXT, CSV, XLSX, Images — up to 50 MB each
        </p>
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-3 mb-4">
            <div className="relative flex-1">
              <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search documents…"
                className="pl-9"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
            <Select value={dept} onValueChange={setDept}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Department" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Departments</SelectItem>
                {[
                  "Maintenance",
                  "Safety",
                  "Operations",
                  "Quality",
                  "Compliance",
                  "Engineering",
                ].map((d) => (
                  <SelectItem key={d} value={d}>
                    {d}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button variant="outline" className="gap-2">
              <Filter className="h-4 w-4" /> More filters
            </Button>
          </div>

          <div className="rounded-lg border overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Document</TableHead>
                  <TableHead>Department</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Uploaded By</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((d) => {
                  const Icon = ICONS[d.type];
                  return (
                    <TableRow key={d.id}>
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="h-9 w-9 rounded-md bg-muted flex items-center justify-center shrink-0">
                            <Icon className="h-4 w-4 text-muted-foreground" />
                          </div>
                          <div className="min-w-0">
                            <div className="truncate">{d.name}</div>
                            <div className="flex gap-1 mt-1">
                              {d.tags.slice(0, 2).map((t) => (
                                <Badge key={t} variant="outline" className="text-[10px] py-0">
                                  {t}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>{d.department}</TableCell>
                      <TableCell>
                        <Badge variant="secondary">{d.type}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={cn(
                            d.status === "Indexed" && "border-success text-success",
                            d.status === "Processing" && "border-warning text-warning",
                            d.status === "Failed" && "border-destructive text-destructive",
                          )}
                        >
                          {d.status}
                        </Badge>
                      </TableCell>
                      <TableCell>{d.uploadedBy}</TableCell>
                      <TableCell className="text-muted-foreground">{d.date}</TableCell>
                      <TableCell className="text-muted-foreground">{d.size}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button size="icon" variant="ghost">
                            <Eye className="h-3.5 w-3.5" />
                          </Button>
                          <Button size="icon" variant="ghost">
                            <Download className="h-3.5 w-3.5" />
                          </Button>
                          <Button size="icon" variant="ghost">
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
