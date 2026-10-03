import { Database, Columns3, Rows3, ShieldCheck, AlertTriangle } from "lucide-react";
import type { Dataset } from "@/lib/mock-data";

export function DatasetSummary({ d }: { d: Dataset }) {
  const typeCounts = d.columnTypes.reduce<Record<string, number>>((acc, c) => {
    acc[c.type] = (acc[c.type] ?? 0) + 1;
    return acc;
  }, {});
  const status = d.cleaningStatus;

  return (
    <div className="rounded-xl border border-border bg-card p-4 shadow-[var(--shadow-card)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary">
            <Database className="h-5 w-5 text-muted-foreground" />
          </div>
          <div>
            <div className="text-sm font-semibold">{d.name}</div>
            <div className="text-xs text-muted-foreground">Uploaded {d.uploadedAt} · {d.size}</div>
          </div>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <Pill>{d.rows.toLocaleString()} rows</Pill>
          <Pill>{d.columns} columns</Pill>
          <StatusPill status={status} />
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat icon={<Rows3 className="h-3.5 w-3.5" />} label="Rows" value={d.rows.toLocaleString()} />
        <Stat icon={<Columns3 className="h-3.5 w-3.5" />} label="Columns" value={String(d.columns)} />
        <Stat icon={<Database className="h-3.5 w-3.5" />} label="Numeric / Cat." value={`${typeCounts.numeric ?? 0} / ${typeCounts.category ?? 0}`} />
        <Stat
          icon={status === "clean" ? <ShieldCheck className="h-3.5 w-3.5" /> : <AlertTriangle className="h-3.5 w-3.5" />}
          label="Cleaning"
          value={status === "clean" ? "Clean" : status === "warnings" ? "2 warnings" : "Issues"}
        />
      </div>
    </div>
  );
}

function Pill({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full border border-border bg-secondary px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
      {children}
    </span>
  );
}

function StatusPill({ status }: { status: Dataset["cleaningStatus"] }) {
  const map = {
    clean: { bg: "bg-[oklch(0.95_0.05_160)]", fg: "text-[oklch(0.35_0.1_160)]", label: "Clean" },
    warnings: { bg: "bg-[oklch(0.96_0.07_75)]", fg: "text-[oklch(0.4_0.12_60)]", label: "2 warnings" },
    issues: { bg: "bg-[oklch(0.95_0.07_25)]", fg: "text-[oklch(0.45_0.18_25)]", label: "Issues" },
  }[status];
  return <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${map.bg} ${map.fg}`}>{map.label}</span>;
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-secondary/40 p-3">
      <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-muted-foreground">
        {icon} {label}
      </div>
      <div className="mt-1 text-sm font-semibold tabular-nums">{value}</div>
    </div>
  );
}
