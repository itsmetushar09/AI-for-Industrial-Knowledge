import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  MessageSquarePlus,
  Pin,
  Folder,
  Send,
  Paperclip,
  Sparkles,
  FileText,
  Download,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types";

export const Route = createFileRoute("/_app/copilot")({
  component: CopilotPage,
});

const SUGGESTIONS = [
  "Why did Pump A fail?",
  "Show maintenance history of Compressor C12.",
  "Which SOP mentions emergency shutdown?",
  "Summarize the latest Boiler 4 inspection report.",
  "Show all documents related to Boiler 4.",
  "Find similar incidents to last week's Pump A failure.",
  "Generate a Root Cause Analysis for Conveyor B3.",
];

function CopilotPage() {
  const { data: history } = useQuery({ queryKey: ["chatHistory"], queryFn: api.chatHistory });
  const [active, setActive] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const queryClient = useQueryClient();
  const initializedHistory = useRef(false);

  useEffect(() => {
    if (!initializedHistory.current && history?.length) {
      initializedHistory.current = true;
      setActive(history[0].id);
      setMessages(history[0].messages);
    }
  }, [history]);

  const activeConv = history?.find((c) => c.id === active);

  const send = async (q?: string) => {
    const text = (q ?? input).trim();
    if (!text) return;
    setInput("");
    const userMsg: ChatMessage = {
      id: `u_${Date.now()}`,
      role: "user",
      content: text,
      createdAt: new Date().toISOString(),
    };
    setMessages((m) => [...m, userMsg]);
    setStreaming(true);
    try {
      const reply = await api.chat(text, active);
      setMessages((m) => [...m, reply]);
      setActive(reply.conversationId ?? active);
      await queryClient.invalidateQueries({ queryKey: ["chatHistory"] });
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Chat request failed");
    } finally {
      setStreaming(false);
    }
  };

  return (
    <div className="h-[calc(100vh-8rem)] grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-4">
      <Card className="hidden lg:flex flex-col p-0 overflow-hidden">
        <div className="p-3 border-b">
          <Button
            className="w-full justify-start gap-2"
            onClick={() => {
              setMessages([]);
              setActive(null);
            }}
          >
            <MessageSquarePlus className="h-4 w-4" /> New Chat
          </Button>
        </div>
        <ScrollArea className="flex-1">
          <div className="p-3 space-y-4">
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">
                Pinned
              </p>
              {(history ?? [])
                .filter((c) => c.pinned)
                .map((c) => (
                  <button
                    key={c.id}
                    onClick={() => {
                      setActive(c.id);
                      setMessages(c.messages);
                    }}
                    className={cn(
                      "w-full text-left px-2 py-2 rounded-md text-sm hover:bg-muted flex items-center gap-2",
                      active === c.id && "bg-muted font-medium",
                    )}
                  >
                    <Pin className="h-3 w-3 text-primary" />
                    {c.title}
                  </button>
                ))}
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">
                Folders
              </p>
              {["Maintenance", "Safety", "Compliance"].map((f) => (
                <div
                  key={f}
                  className="text-sm flex items-center gap-2 px-2 py-1.5 text-muted-foreground"
                >
                  <Folder className="h-3.5 w-3.5" />
                  {f}
                </div>
              ))}
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">
                Recent
              </p>
              {(history ?? []).map((c) => (
                <button
                  key={c.id}
                  onClick={() => {
                    setActive(c.id);
                    setMessages(c.messages);
                  }}
                  className={cn(
                    "w-full text-left px-2 py-2 rounded-md text-sm hover:bg-muted truncate block",
                    active === c.id && "bg-muted font-medium",
                  )}
                >
                  {c.title}
                  <span className="block text-[10px] text-muted-foreground">{c.updatedAt}</span>
                </button>
              ))}
            </div>
          </div>
        </ScrollArea>
      </Card>

      <Card className="flex flex-col overflow-hidden p-0">
        <div className="border-b px-4 py-3 flex items-center justify-between">
          <div>
            <h2 className="font-semibold">{activeConv?.title ?? "New conversation"}</h2>
            <p className="text-xs text-muted-foreground">
              Grounded answers from your indexed documents
            </p>
          </div>
          <Button variant="outline" size="sm" className="gap-2">
            <Download className="h-3.5 w-3.5" /> Export
          </Button>
        </div>

        <ScrollArea className="flex-1">
          <div className="max-w-3xl mx-auto px-4 md:px-6 py-6 space-y-5">
            {messages.length === 0 && (
              <div className="text-center py-10">
                <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary mb-3">
                  <Sparkles className="h-6 w-6" />
                </div>
                <h3 className="text-lg font-semibold">Ask anything about your plant</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Try one of these to get started
                </p>
                <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      className="border rounded-lg p-3 text-sm hover:bg-muted/50 transition"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <AnimatePresence>
              {messages.map((m) => (
                <motion.div
                  key={m.id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={cn("flex gap-3", m.role === "user" ? "justify-end" : "justify-start")}
                >
                  {m.role === "assistant" && (
                    <div className="h-8 w-8 rounded-lg bg-primary text-primary-foreground flex items-center justify-center shrink-0">
                      <Sparkles className="h-4 w-4" />
                    </div>
                  )}
                  <div
                    className={cn(
                      "rounded-2xl px-4 py-3 max-w-[85%] whitespace-pre-wrap text-sm leading-relaxed",
                      m.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted",
                    )}
                  >
                    {m.content}
                    {m.citations && (
                      <div className="mt-3 pt-3 border-t border-border/40 flex flex-wrap gap-2">
                        {m.citations.map((c, i) => (
                          <Badge key={i} variant="secondary" className="gap-1 font-normal">
                            <FileText className="h-3 w-3" />
                            {c.doc}
                            {c.page ? ` · p.${c.page}` : ""}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {streaming && (
              <div className="flex gap-3">
                <div className="h-8 w-8 rounded-lg bg-primary text-primary-foreground flex items-center justify-center">
                  <Sparkles className="h-4 w-4" />
                </div>
                <div className="bg-muted rounded-2xl px-4 py-3 flex gap-1">
                  {[0, 1, 2].map((i) => (
                    <span
                      key={i}
                      className="h-2 w-2 rounded-full bg-foreground/40 animate-bounce"
                      style={{ animationDelay: `${i * 120}ms` }}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        <div className="border-t p-3">
          <div className="max-w-3xl mx-auto flex gap-2">
            <Button variant="outline" size="icon">
              <Paperclip className="h-4 w-4" />
            </Button>
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), send())}
              placeholder="Ask about machines, SOPs, incidents…"
              className="h-11"
            />
            <Button
              className="gap-2 h-11"
              onClick={() => send()}
              disabled={streaming || !input.trim()}
            >
              <Send className="h-4 w-4" /> Send
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
