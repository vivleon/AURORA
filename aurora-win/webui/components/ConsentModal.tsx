import * as React from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";


type ConsentReq = {
purpose?: string; scope?: string; risk?: "low"|"medium"|"high"; ttl_hours?: number;
rationale?: { why?: string; how?: string };
};


export default function ConsentModal({ open, onOpenChange, request, onDecision }:{
open:boolean; onOpenChange:(v:boolean)=>void; request?: ConsentReq; onDecision?:(ok:boolean)=>void;
}){
return (
<Dialog open={open} onOpenChange={onOpenChange}>
<DialogContent className="max-w-xl">
<DialogHeader>
<DialogTitle className="flex items-center gap-2">
작업 승인 필요
{request?.risk && <Badge variant={request?.risk === "high"?"destructive":"default"}>{request.risk?.toUpperCase()}</Badge>}
</DialogTitle>
</DialogHeader>


<div className="space-y-3 text-sm">
<div><span className="font-medium">Purpose:</span> {request?.purpose ?? "-"}</div>
<div><span className="font-medium">Scope:</span> {request?.scope ?? "-"}</div>
<div><span className="font-medium">TTL:</span> {request?.ttl_hours ?? 24}h</div>


{/* Explainability block */}
<div className="rounded-lg border p-3 bg-muted/40">
<div className="text-xs uppercase tracking-wide opacity-70 mb-1">Why / How</div>
<p className="text-sm mb-1">{request?.rationale?.why ?? ""}</p>
<p className="text-xs opacity-80">{request?.rationale?.how ?? ""}</p>
</div>
</div>


<div className="flex justify-end gap-2 pt-2">
<Button variant="secondary" onClick={()=>onDecision?.(false)}>거부</Button>
<Button onClick={()=>onDecision?.(true)}>동의</Button>
</div>
</DialogContent>
</Dialog>
);
}