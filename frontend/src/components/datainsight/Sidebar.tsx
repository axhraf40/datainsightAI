import { useRef, useState } from "react";
import {
  Upload, FileSpreadsheet, MessagesSquare, Lightbulb, User2,
  Plus, MoreHorizontal, Settings, FileText,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { sampleDataset, otherDatasets, conversations, suggestedQuestions, type Dataset } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

interface Props {
  authed: boolean;
  activeDataset: Dataset | null;
  onUpload: (name: string) => void;
  onPickSuggestion: (q: string) => void;
  onNewChat: () => void;
  onSignIn: () => void;
}

export function Sidebar({ authed, activeDataset, onUpload, onPickSuggestion, onNewChat, onSignIn }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = (f?: File | null) => {
    if (!f) return;
    onUpload(f.name);
  };

  return (
    <aside className="hidden w-[300px] shrink-0 flex-col border-r border-sidebar-border bg-sidebar md:flex">
      <div className="flex flex-col gap-5 overflow-y-auto p-4">
        {/* Upload */}
        <section>
          <SectionLabel icon={<Upload className="h-3.5 w-3.5" />}>Upload data</SectionLabel>
          <label
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files?.[0]); }}
            className={cn(
              "mt-2 flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed bg-secondary/40 px-3 py-5 text-center transition",
              dragOver ? "border-primary bg-secondary" : "border-border hover:bg-secondary"
            )}
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-card shadow-[var(--shadow-card)]">
              <Upload className="h-4 w-4 text-muted-foreground" />
            </div>
            <div className="mt-2 text-xs font-medium">Drop CSV or Excel</div>
            <div className="text-[11px] text-muted-foreground">or click to browse · max 50MB</div>
            <input
              ref={fileRef}
              type="file"
              accept=".csv,.xls,.xlsx"
              className="hidden"
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
          </label>
        </section>

        {/* Files */}
        <section>
          <div className="flex items-center justify-between">
            <SectionLabel icon={<FileSpreadsheet className="h-3.5 w-3.5" />}>Files</SectionLabel>
            {!authed && <span className="text-[10px] text-muted-foreground">session only</span>}
          </div>
          <ul className="mt-2 space-y-1">
            {activeDataset && <FileRow name={activeDataset.name} meta={`${activeDataset.rows.toLocaleString()} rows`} active />}
            {authed && otherDatasets.map((d) => (
              <FileRow key={d.id} name={d.name} meta={`${d.rows.toLocaleString()} rows · ${d.uploadedAt}`} />
            ))}
            {!authed && !activeDataset && (
              <li className="rounded-md border border-dashed border-border px-3 py-3 text-[11px] text-muted-foreground">
                No files yet. Upload one to begin.
              </li>
            )}
          </ul>
        </section>

        {/* Conversations */}
        <section>
          <div className="flex items-center justify-between">
            <SectionLabel icon={<MessagesSquare className="h-3.5 w-3.5" />}>Conversations</SectionLabel>
            <button
              onClick={onNewChat}
              className="flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground hover:bg-secondary"
              aria-label="New chat"
            >
              <Plus className="h-3.5 w-3.5" />
            </button>
          </div>
          <ul className="mt-2 space-y-0.5">
            {(authed ? conversations : conversations.slice(0, 1)).map((c, i) => (
              <li key={c.id}>
                <button className={cn(
                  "group flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-[13px] hover:bg-sidebar-accent",
                  i === 0 && "bg-sidebar-accent"
                )}>
                  <span className="truncate">{c.title}</span>
                  <MoreHorizontal className="h-3.5 w-3.5 opacity-0 group-hover:opacity-100 text-muted-foreground" />
                </button>
              </li>
            ))}
            {!authed && (
              <li className="rounded-md bg-secondary/60 px-2 py-2 text-[11px] text-muted-foreground">
                Sign in to save and revisit conversations.
              </li>
            )}
          </ul>
        </section>

        {/* Suggested */}
        <section>
          <SectionLabel icon={<Lightbulb className="h-3.5 w-3.5" />}>Suggested questions</SectionLabel>
          <ul className="mt-2 space-y-1.5">
            {suggestedQuestions.slice(0, 4).map((q) => (
              <li key={q}>
                <button
                  onClick={() => onPickSuggestion(q)}
                  className="w-full rounded-md border border-border bg-card px-2.5 py-2 text-left text-[12px] leading-snug text-muted-foreground hover:border-primary/30 hover:text-foreground"
                >
                  {q}
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>

      {/* Profile */}
      <div className="mt-auto border-t border-sidebar-border p-3">
        {authed ? (
          <div className="flex items-center gap-2.5 rounded-lg p-1.5 hover:bg-sidebar-accent">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">AM</div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-[13px] font-medium">Alex Morgan</div>
              <div className="truncate text-[11px] text-muted-foreground">alex@acme.co</div>
            </div>
            <button className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-card" aria-label="Settings">
              <Settings className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <div className="rounded-lg border border-border bg-secondary/60 p-3">
            <div className="flex items-center gap-2 text-xs font-medium">
              <User2 className="h-3.5 w-3.5" /> Guest mode
            </div>
            <p className="mt-1 text-[11px] text-muted-foreground">
              3 questions per session. Sign in for unlimited chat and history.
            </p>
            <Button size="sm" className="mt-2 w-full" onClick={onSignIn}>
              Sign in to unlock
            </Button>
          </div>
        )}
      </div>
    </aside>
  );
}

function SectionLabel({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
      {icon}
      {children}
    </div>
  );
}

function FileRow({ name, meta, active }: { name: string; meta: string; active?: boolean }) {
  return (
    <li>
      <button className={cn(
        "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left hover:bg-sidebar-accent",
        active && "bg-sidebar-accent"
      )}>
        <FileText className="h-3.5 w-3.5 text-muted-foreground" />
        <div className="min-w-0 flex-1">
          <div className="truncate text-[13px]">{name}</div>
          <div className="truncate text-[11px] text-muted-foreground">{meta}</div>
        </div>
      </button>
    </li>
  );
}
