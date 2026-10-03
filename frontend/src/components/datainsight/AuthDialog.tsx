import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Sparkles } from "lucide-react";

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onAuthed: () => void;
}

export function AuthDialog({ open, onOpenChange, onAuthed }: Props) {
  const [tab, setTab] = useState("signin");
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <Sparkles className="h-5 w-5" />
          </div>
          <DialogTitle className="text-center">Continue with DataInsight AI</DialogTitle>
          <DialogDescription className="text-center">
            Your uploaded file and conversation will be preserved.
          </DialogDescription>
        </DialogHeader>
        <Tabs value={tab} onValueChange={setTab} className="mt-2">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="signin">Sign in</TabsTrigger>
            <TabsTrigger value="signup">Register</TabsTrigger>
            <TabsTrigger value="reset">Reset</TabsTrigger>
          </TabsList>
          <TabsContent value="signin" className="mt-4 space-y-3">
            <Field label="Email" type="email" placeholder="you@company.com" />
            <Field label="Password" type="password" placeholder="••••••••" />
            <Button className="w-full" onClick={onAuthed}>Sign in</Button>
          </TabsContent>
          <TabsContent value="signup" className="mt-4 space-y-3">
            <Field label="Full name" placeholder="Alex Morgan" />
            <Field label="Email" type="email" placeholder="you@company.com" />
            <Field label="Password" type="password" placeholder="At least 8 characters" />
            <Button className="w-full" onClick={onAuthed}>Create account</Button>
          </TabsContent>
          <TabsContent value="reset" className="mt-4 space-y-3">
            <Field label="Email" type="email" placeholder="you@company.com" />
            <Button className="w-full" variant="outline" onClick={() => setTab("signin")}>Send reset link</Button>
          </TabsContent>
        </Tabs>
        <div className="mt-2 text-center text-[11px] text-muted-foreground">
          By continuing you agree to our Terms and Privacy Policy.
        </div>
      </DialogContent>
    </Dialog>
  );
}

function Field({ label, ...props }: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs">{label}</Label>
      <Input {...props} />
    </div>
  );
}
