import { useState } from "react";
import { Sparkles, User2, FileDown, ChevronDown, Copy, Check } from "lucide-react";
import type { ChatMessage, ChartData, TableData } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export function MessageBubble({ m }: { m: ChatMessage }) {
  if (m.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="flex max-w-[80%] items-start gap-2.5">
          <div className="rounded-2xl rounded-tr-sm bg-primary px-4 py-2.5 text-sm text-primary-foreground">
            {m.text}
          </div>
          <Avatar role="user" />
        </div>
      </div>
    );
  }
  return (
    <div className="flex items-start gap-3">
      <Avatar role="assistant" />
      <div className="min-w-0 flex-1 space-y-3">
        {m.text?.trim() ? (
          <div className="prose-sm max-w-none text-sm leading-relaxed text-foreground">
            <RichText text={m.text} />
          </div>
        ) : null}
        {m.chart && <ChartBlock chart={m.chart} />}
        {m.table && <TableBlock table={m.table} />}
        {m.code && <CodeBlock code={m.code} />}
        {m.pdfName && (
          <button className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground shadow-[var(--shadow-card)] hover:bg-secondary">
            <FileDown className="h-3.5 w-3.5" /> Download report · {m.pdfName}
          </button>
        )}
      </div>
    </div>
  );
}

function Avatar({ role }: { role: "user" | "assistant" }) {
  if (role === "user") {
    return (
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-secondary text-muted-foreground">
        <User2 className="h-3.5 w-3.5" />
      </div>
    );
  }
  return (
    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
      <Sparkles className="h-3.5 w-3.5" />
    </div>
  );
}

function RichText({ text }: { text: string }) {
  // tiny markdown: **bold** and `code`
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return (
    <p>
      {parts.map((p, i) => {
        if (p.startsWith("**") && p.endsWith("**"))
          return <strong key={i} className="font-semibold">{p.slice(2, -2)}</strong>;
        if (p.startsWith("`") && p.endsWith("`"))
          return <code key={i} className="rounded bg-secondary px-1 py-0.5 text-[12px] font-mono">{p.slice(1, -1)}</code>;
        return <span key={i}>{p}</span>;
      })}
    </p>
  );
}

function TableBlock({ table }: { table: TableData }) {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card shadow-[var(--shadow-card)]">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-secondary/60">
            <tr>
              {table.columns.map((c) => (
                <th key={c} className="px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row, ri) => (
              <tr key={ri} className="border-t border-border">
                {row.map((cell, ci) => (
                  <td key={ci} className={cn("px-3 py-2 tabular-nums", ci === 0 && "font-medium")}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ChartBlock({ chart }: { chart: ChartData }) {
  const max = Math.max(...chart.bars.map((b) => b.value));
  return (
    <div className="rounded-xl border border-border bg-card p-4 shadow-[var(--shadow-card)]">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-xs font-semibold text-foreground">{chart.title}</div>
        <div className="text-[11px] text-muted-foreground">in thousands USD</div>
      </div>
      <div className="space-y-2">
        {chart.bars.map((b) => (
          <div key={b.label} className="flex items-center gap-3">
            <div className="w-28 truncate text-[12px] text-muted-foreground">{b.label}</div>
            <div className="relative h-6 flex-1 overflow-hidden rounded-md bg-secondary">
              <div
                className="h-full rounded-md bg-primary"
                style={{ width: `${(b.value / max) * 100}%` }}
              />
            </div>
            <div className="w-16 text-right text-[12px] font-medium tabular-nums">${b.value}k</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function CodeBlock({ code }: { code: string }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card shadow-[var(--shadow-card)]">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-3 py-2 text-left text-xs font-medium hover:bg-secondary/60"
      >
        <span className="text-muted-foreground">View SQL query</span>
        <ChevronDown className={cn("h-3.5 w-3.5 text-muted-foreground transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div className="relative border-t border-border bg-[oklch(0.98_0.005_247)]">
          <button
            onClick={() => {
              navigator.clipboard.writeText(code);
              setCopied(true);
              setTimeout(() => setCopied(false), 1500);
            }}
            className="absolute right-2 top-2 inline-flex items-center gap-1 rounded-md border border-border bg-card px-1.5 py-1 text-[11px] text-muted-foreground hover:text-foreground"
          >
            {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />} {copied ? "Copied" : "Copy"}
          </button>
          <pre className="overflow-x-auto p-3 text-[12px] leading-relaxed text-foreground"><code>{code}</code></pre>
        </div>
      )}
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div className="flex items-start gap-3">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
        <Sparkles className="h-3.5 w-3.5" />
      </div>
      <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-sm border border-border bg-card px-3 py-2.5 shadow-[var(--shadow-card)]">
        <Dot /> <Dot delay={0.15} /> <Dot delay={0.3} />
        <span className="ml-1 text-xs text-muted-foreground">Analyzing your dataset…</span>
      </div>
    </div>
  );
}

function Dot({ delay = 0 }: { delay?: number }) {
  return (
    <span
      className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground"
      style={{ animationDelay: `${delay}s`, animationDuration: "1s" }}
    />
  );
}
