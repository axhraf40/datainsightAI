import { Sparkles, LogIn, User2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  authed: boolean;
  onSignIn: () => void;
  onSignOut: () => void;
}

export function TopBar({ authed, onSignIn, onSignOut }: Props) {
  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-card/80 px-4 backdrop-blur md:px-6">
      <div className="flex items-center gap-2.5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Sparkles className="h-4 w-4" />
        </div>
        <div className="leading-tight">
          <div className="text-sm font-semibold tracking-tight">DataInsight AI</div>
          <div className="text-[11px] text-muted-foreground">E-commerce data analyst</div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {authed ? (
          <>
            <span className="hidden items-center gap-1.5 rounded-full border border-border bg-secondary px-2.5 py-1 text-xs font-medium text-muted-foreground sm:inline-flex">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-success)]" />
              Pro plan
            </span>
            <button
              onClick={onSignOut}
              className="flex items-center gap-2 rounded-full border border-border bg-card px-2 py-1 pr-3 text-sm hover:bg-secondary"
            >
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-[11px] font-semibold text-primary-foreground">
                AM
              </div>
              <span className="hidden sm:inline">Alex Morgan</span>
            </button>
          </>
        ) : (
          <>
            <span className="hidden items-center gap-1.5 rounded-full border border-border bg-secondary px-2.5 py-1 text-xs font-medium text-muted-foreground md:inline-flex">
              <User2 className="h-3 w-3" /> Guest mode
            </span>
            <Button size="sm" variant="outline" onClick={onSignIn} className="gap-1.5">
              <LogIn className="h-3.5 w-3.5" /> Sign in
            </Button>
            <Button size="sm" onClick={onSignIn}>
              Create account
            </Button>
          </>
        )}
      </div>
    </header>
  );
}
