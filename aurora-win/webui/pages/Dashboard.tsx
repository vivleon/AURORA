// ...inside Overview cards rendering, inject Why/How chips when last consent exists
import { WhyHowChips } from "@/webui/components/WhyHowChips";
// assume `lastConsent` fetched from `/dash/consent/timeline?limit=1`
{/* beneath KPI cards */}
<WhyHowChips why={lastConsent?.rationale?.why} how={lastConsent?.rationale?.how} />