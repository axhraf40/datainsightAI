import { useState, type KeyboardEvent } from "react";
import { ArrowUp, Lock, Paperclip } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Props {
  disabled?: boolean;
  remaining?: number | null;
  onSend: (text: string) => void;
  onSignIn: () => void;
}

export function Composer({ disabled, remaining, onSend, onSignIn }: Props) {
  const [value, setValue] = useState("");
  const submit = () => {
    const v = value.trim();
    if (!v || disabled) return;
    onSend(v);
    setValue("");
  };
  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  if (disabled) {
    return (
      <div className="rounded-2xl border border-border bg-card p-4 shadow-[var(--shadow-card)]">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-secondary text-muted-foreground">
            <Lock className="h-4 w-4" />
          </div>
          <div className="flex-1">
            <div className="text-sm font-semibold">You've reached the 3-question guest limit</div>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Create a free account to keep chatting with this dataset — your file and conversation will be preserved.
            </p>
            <div className="mt-3 flex gap-2">
              <Button size="sm" onClick={onSignIn}>Create free account</Button>
              <Button size="sm" variant="outline" onClick={onSignIn}>Sign in</Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-border bg-card shadow-[var(--shadow-card)] focus-within:border-primary/40 focus-within:ring-2 focus-within:ring-primary/10">
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKey}
        rows={1}
        placeholder="Ask anything about your dataset…"
        className="w-full resize-none rounded-2xl bg-transparent px-4 pt-3.5 text-sm placeholder:text-muted-foreground focus:outline-none"
      />
      <div className="flex items-center justify-between px-3 pb-2.5 pt-1">
        <div className="flex items-center gap-2">
          <button className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-secondary" aria-label="Attach">
            <Paperclip className="h-3.5 w-3.5" />
          </button>
          {remaining !== null && remaining !== undefined && (
            <span className={cn(
              "rounded-full border border-border bg-secondary px-2 py-0.5 text-[11px] font-medium",
              remaining <= 1 ? "text-[oklch(0.5_0.15_30)]" : "text-muted-foreground"
            )}>
              {remaining} of 3 guest questions left
            </span>
          )}
        </div>
        <button
          onClick={submit}
          disabled={!value.trim()}
          className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground disabled:opacity-40"
          aria-label="Send"
        >
          <ArrowUp className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
