import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { TopBar } from "@/components/datainsight/TopBar";
import { Sidebar } from "@/components/datainsight/Sidebar";
import { EmptyState } from "@/components/datainsight/EmptyState";
import { DatasetSummary } from "@/components/datainsight/DatasetSummary";
import { MessageBubble, TypingIndicator } from "@/components/datainsight/ChatMessage";
import { Composer } from "@/components/datainsight/Composer";
import { AuthDialog } from "@/components/datainsight/AuthDialog";
import { initialMessages, sampleDataset, suggestedQuestions, type ChatMessage, type Dataset } from "@/lib/mock-data";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "DataInsight AI — Chat with your e-commerce data" },
      { name: "description", content: "Upload CSV or Excel and ask questions in plain English. Get tables, charts and PDF reports." },
    ],
  }),
  component: Dashboard,
});

const GUEST_LIMIT = 3;

function Dashboard() {
  const [authed, setAuthed] = useState(false);
  const [authOpen, setAuthOpen] = useState(false);
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [thinking, setThinking] = useState(false);
  const [guestAsked, setGuestAsked] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, thinking]);

  const handleUpload = (name: string) => {
    const d: Dataset = { ...sampleDataset, name: name || sampleDataset.name };
    setDataset(d);
    setMessages([
      {
        id: crypto.randomUUID(),
        role: "assistant",
        text: `I profiled **${d.name}** — ${d.rows.toLocaleString()} rows × ${d.columns} columns. I detected 5 numeric metrics, 3 categories, and flagged 2 minor data quality warnings. What would you like to explore?`,
      },
    ]);
  };

  const loadDemo = () => {
    setDataset(sampleDataset);
    setMessages(initialMessages);
  };

  const send = (text: string) => {
    if (!authed && guestAsked >= GUEST_LIMIT) return;
    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", text };
    setMessages((m) => [...m, userMsg]);
    setThinking(true);
    if (!authed) setGuestAsked((n) => n + 1);
    setTimeout(() => {
      setThinking(false);
      setMessages((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: "Here's what I found in your dataset based on your question. The breakdown below highlights the **top contributors** and a quick visualisation.",
          table: initialMessages[2].table,
          chart: initialMessages[2].chart,
          code: initialMessages[2].code,
          pdfName: "insight-report.pdf",
        },
      ]);
    }, 1100);
  };

  const limitReached = !authed && guestAsked >= GUEST_LIMIT;
  const remaining = authed ? null : Math.max(0, GUEST_LIMIT - guestAsked);

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <TopBar
        authed={authed}
        onSignIn={() => setAuthOpen(true)}
        onSignOut={() => setAuthed(false)}
      />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          authed={authed}
          activeDataset={dataset}
          onUpload={handleUpload}
          onPickSuggestion={(q) => dataset && send(q)}
          onNewChat={() => setMessages(dataset ? messages.slice(0, 1) : [])}
          onSignIn={() => setAuthOpen(true)}
        />

        <main className="flex flex-1 flex-col">
          {!dataset ? (
            <div className="flex-1 overflow-y-auto">
              <EmptyState onUpload={handleUpload} />
              <div className="mx-auto mb-10 max-w-2xl px-4 text-center">
                <button
                  onClick={loadDemo}
                  className="text-xs font-medium text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
                >
                  Or explore with sample dataset →
                </button>
              </div>
            </div>
          ) : (
            <>
              <div ref={scrollRef} className="flex-1 overflow-y-auto">
                <div className="mx-auto w-full max-w-3xl space-y-5 px-4 py-6 md:px-6">
                  <DatasetSummary d={dataset} />

                  {messages.length <= 1 && (
                    <div className="rounded-xl border border-border bg-card p-4 shadow-[var(--shadow-card)]">
                      <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                        Try one of these
                      </div>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {suggestedQuestions.map((q) => (
                          <button
                            key={q}
                            onClick={() => send(q)}
                            className="rounded-full border border-border bg-secondary px-3 py-1.5 text-xs text-foreground hover:border-primary/30"
                          >
                            {q}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="space-y-5 pt-2">
                    {messages.map((m) => <MessageBubble key={m.id} m={m} />)}
                    {thinking && <TypingIndicator />}
                  </div>
                </div>
              </div>

              <div className="border-t border-border bg-background/80 px-4 py-3 backdrop-blur md:px-6">
                <div className="mx-auto max-w-3xl">
                  <Composer
                    disabled={limitReached}
                    remaining={remaining}
                    onSend={send}
                    onSignIn={() => setAuthOpen(true)}
                  />
                  <p className="mt-2 text-center text-[11px] text-muted-foreground">
                    DataInsight AI can make mistakes. Verify important figures before sharing.
                  </p>
                </div>
              </div>
            </>
          )}
        </main>
      </div>

      <AuthDialog
        open={authOpen}
        onOpenChange={setAuthOpen}
        onAuthed={() => { setAuthed(true); setAuthOpen(false); setGuestAsked(0); }}
      />
    </div>
  );
}
