import { useCallback, useState } from "react";
import type { ConsentRequest } from "./webui_ConsentModal";

export function useConsent(apiBase = "/consent") {
  const [open, setOpen] = useState(false);
  const [request, setRequest] = useState<ConsentRequest | null>(null);

  const ask = useCallback(async (req: ConsentRequest) => {
    setRequest(req);
    setOpen(true);
  }, []);

  return { open, setOpen, request, ask, apiBase };
}

// Example usage in a page/component
// const { open, setOpen, request, ask } = useConsent();
// <ConsentModal open={open} onOpenChange={setOpen} request={request} />
