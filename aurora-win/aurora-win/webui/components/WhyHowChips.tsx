import * as React from "react";


export function WhyHowChips({ why, how }:{ why?:string; how?:string }){
if(!why && !how) return null;
return (
<div className="flex flex-wrap gap-2">
{why && <span className="text-xs rounded-full border px-2 py-1 bg-muted/50">WHY: {why}</span>}
{how && <span className="text-xs rounded-full border px-2 py-1 bg-muted/50">HOW: {how}</span>}
</div>
);
}

