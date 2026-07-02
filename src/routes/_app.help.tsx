import { createFileRoute } from "@tanstack/react-router";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Search, BookOpen, MessageCircleQuestion, FileVideo } from "lucide-react";

export const Route = createFileRoute("/_app/help")({
  component: HelpPage,
});

const FAQ = [
  {
    q: "How do I upload documents?",
    a: "Go to Documents → click Upload or drag files into the dropzone. Supported formats: PDF, DOCX, TXT, CSV, XLSX, images.",
  },
  {
    q: "How does the AI Copilot ground its answers?",
    a: "Every answer is generated using only your uploaded documents and includes inline citations to the source files.",
  },
  {
    q: "Can I export a conversation?",
    a: "Yes — open any conversation in the Copilot and click Export.",
  },
  {
    q: "How do I add new users?",
    a: "Administrators can invite users from the Users page and assign one of the predefined roles.",
  },
];

function HelpPage() {
  return (
    <div>
      <PageHeader title="Help & Support" description="Answers, guides and resources." />

      <div className="relative max-w-xl mb-6">
        <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <Input placeholder="Search help articles…" className="pl-9 h-11" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {[
          { icon: BookOpen, t: "Documentation", d: "Read product guides" },
          { icon: FileVideo, t: "Video Tutorials", d: "Watch 5-minute walkthroughs" },
          { icon: MessageCircleQuestion, t: "Contact Support", d: "Email support@indus.ai" },
        ].map((it) => (
          <Card key={it.t} className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="p-5">
              <it.icon className="h-6 w-6 text-primary mb-3" />
              <h3 className="font-semibold">{it.t}</h3>
              <p className="text-sm text-muted-foreground mt-1">{it.d}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardContent className="p-6">
          <h2 className="font-semibold mb-4">Frequently asked</h2>
          <div className="divide-y">
            {FAQ.map((f) => (
              <div key={f.q} className="py-4">
                <p className="font-medium">{f.q}</p>
                <p className="text-sm text-muted-foreground mt-1">{f.a}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
