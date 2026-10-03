import { useRef, useState } from "react";
import { Upload, FileSpreadsheet, MessageSquare, FileDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function EmptyState({ onUpload }: { onUpload: (name: string) => void }) {
  const [drag, setDrag] = useState(false);
  const ref = useRef<HTMLInputElement>(null);
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col items-center px-4 py-10 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-[var(--shadow-elevated)]">
        <FileSpreadsheet className="h-6 w-6" />
      </div>
      <h1 className="mt-5 text-2xl font-semibold tracking-tight">Chat with your e-commerce data</h1>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">
        Upload a CSV or Excel file. DataInsight AI will profile your dataset and answer
        your questions with narrative insights, tables, charts, and PDF reports.
      </p>

      <label
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files?.[0]; if (f) onUpload(f.name); }}
        className={cn(
          "mt-7 flex w-full cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed bg-card px-6 py-10 transition shadow-[var(--shadow-card)]",
          drag ? "border-primary bg-secondary" : "border-border hover:bg-secondary/40"
        )}
      >
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-secondary">
          <Upload className="h-4 w-4 text-muted-foreground" />
        </div>
        <div className="mt-3 text-sm font-medium">Drag & drop your file here</div>
        <div className="mt-0.5 text-xs text-muted-foreground">CSV or Excel · up to 50 MB</div>
        <Button size="sm" className="mt-4" onClick={(e) => { e.preventDefault(); ref.current?.click(); }}>
          Browse files
        </Button>
        <input ref={ref} type="file" accept=".csv,.xls,.xlsx" className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) onUpload(f.name); }} />
      </label>

      <div className="mt-7 grid w-full grid-cols-1 gap-2 sm:grid-cols-3">
        <Feature icon={<FileSpreadsheet className="h-4 w-4" />} title="Auto profiling" desc="Detect types, nulls, outliers" />
        <Feature icon={<MessageSquare className="h-4 w-4" />} title="Natural language" desc="Ask in plain English" />
        <Feature icon={<FileDown className="h-4 w-4" />} title="PDF reports" desc="Share polished insights" />
      </div>
    </div>
  );
}

function Feature({ icon, title, desc }: { icon: React.ReactNode; title: string; desc: string }) {
  return (
    <div className="rounded-xl border border-border bg-card p-3 text-left shadow-[var(--shadow-card)]">
      <div className="flex h-7 w-7 items-center justify-center rounded-md bg-secondary text-muted-foreground">{icon}</div>
      <div className="mt-2 text-sm font-medium">{title}</div>
      <div className="text-[11px] text-muted-foreground">{desc}</div>
    </div>
  );
}
