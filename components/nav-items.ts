import {
  Gauge,
  Inbox,
  Lightbulb,
  GitBranch,
  Target,
  Rocket,
} from "lucide-react";

export const NAV_ITEMS = [
  { href: "/overview", label: "Overview", icon: Gauge },
  { href: "/feedback", label: "Feedback", icon: Inbox },
  { href: "/insights", label: "Insights", icon: Lightbulb },
  { href: "/releases", label: "Releases", icon: GitBranch },
  { href: "/opportunities", label: "Opportunities", icon: Target },
  { href: "/action-briefs", label: "Action Briefs", icon: Rocket },
] as const;
