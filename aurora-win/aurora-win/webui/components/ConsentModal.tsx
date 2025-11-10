import React, { useEffect, useMemo, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

// Minimal fallback shadcn types; assume shadcn/ui is installed in the project
// If not, replace with any dialog library or custom components.

export type ConsentPayload = {
  action: string;      // e.g., "mail.send"
  purpose: string;     // e.g., "회의 요약 전송"
  scope: string;       // e.g., "mail|files|system|browser|nlp|ocr"
  risk: "low" | "medium" | "high";
  ttl_hours: number;   // 0 => one-shot
};

export type ConsentRequest = ConsentPayload & {
  session_id: string;
};

export type ConsentModalProps = {
  open: boolean;
  onOpenChange?: (v: boolean) => void;
  request: ConsentRequest | null;
  onApproved?: (consentId: string) => void;
  onDenied?: (consentId: string) => void;
  apiBase?: string; // default "/consent"
};

const RiskChip: React.FC<{ level: "low" | "medium" | "high" }> = ({ level }) => {
  const color = level === "high" ? "destructive" : level === "medium" ? "secondary" : "default" as const;
  return <Badge variant={color as any} className="uppercase tracking-wide">{level}</Badge>;
};

export const ConsentModal: React.FC<ConsentModalProps> = ({ open, onOpenChange, request, onApproved, onDenied, apiBase = "/consent" }) => {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [consentId, setConsentId] = useState<string | null>(null);

  // Issue consent request to backend when modal opens with a payload
  useEffect(() => {
    let cancelled = false;
    async function issue() {
      if (!open || !request) return;
      try {
        setError(null);
        setSubmitting(true);
        const resp = await fetch(`${apiBase}/request`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(request),
        });
        if (!resp.ok) throw new Error(await resp.text());
        const data = await resp.json();
        if (!cancelled) setConsentId(data.consent_id);
      } catch (e: any) {
        if (!cancelled) setError(e?.message ?? "Failed to request consent");
      } finally {
        if (!cancelled) setSubmitting(false);
      }
    }
    issue();
    return () => { cancelled = true };
  }, [open, request, apiBase]);

  const approve = async () => {
    if (!consentId) return;
    setSubmitting(true);
    try {
      const resp = await fetch(`${apiBase}/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ consent_id: consentId, decision: "approved" }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      onApproved?.(consentId);
      onOpenChange?.(false);
    } catch (e: any) {
      setError(e?.message ?? "Approval failed");
    } finally {
      setSubmitting(false);
    }
  };

  const deny = async () => {
    if (!consentId) return;
    setSubmitting(true);
    try {
      const resp = await fetch(`${apiBase}/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ consent_id: consentId, decision: "denied" }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      onDenied?.(consentId);
      onOpenChange?.(false);
    } catch (e: any) {
      setError(e?.message ?? "Denial failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (!request) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[560px]">
        <DialogHeader>
          <DialogTitle className="text-xl">권한 동의 필요</DialogTitle>
          <DialogDescription>
            아래 작업을 진행하려면 사용자의 명시적 동의가 필요합니다.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 mt-2">
          <div className="flex items-center justify-between">
            <div className="text-sm text-muted-foreground">작업(Action)</div>
            <div className="font-medium">{request.action}</div>
          </div>
          <div className="flex items-center justify-between">
            <div className="text-sm text-muted-foreground">목적(Purpose)</div>
            <div className="font-medium max-w-[320px] text-right">{request.purpose}</div>
          </div>
          <div className="flex items-center justify-between">
            <div className="text-sm text-muted-foreground">범위(Scope)</div>
            <div className="font-medium">{request.scope}</div>
          </div>
          <div className="flex items-center justify-between">
            <div className="text-sm text-muted-foreground">유효기간(TTL)</div>
            <div className="font-medium">{request.ttl_hours}h</div>
          </div>
          <div className="flex items-center justify-between">
            <div className="text-sm text-muted-foreground">위험도(Risk)</div>
            <RiskChip level={request.risk} />
          </div>
        </div>

        {error && (
          <div className="text-sm text-red-600 bg-red-50 p-2 rounded-md border border-red-200">
            {error}
          </div>
        )}

        <Separator className="my-2" />

        <DialogFooter className="gap-2">
          <Button variant="secondary" onClick={() => onOpenChange?.(false)} disabled={submitting}>닫기</Button>
          <Button variant="outline" onClick={deny} disabled={submitting || !consentId}>거부</Button>
          <Button onClick={approve} disabled={submitting || !consentId} className="font-semibold">동의하고 진행</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ConsentModal;
