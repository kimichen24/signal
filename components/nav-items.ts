import {
  Gauge,
  Inbox,
  Lightbulb,
  GitBranch,
  Target,
  Rocket,
} from "lucide-react";

export const NAV_ITEMS = [
  { href: "/overview", label: "总览", icon: Gauge },
  { href: "/feedback", label: "反馈", icon: Inbox },
  { href: "/insights", label: "洞察", icon: Lightbulb },
  { href: "/releases", label: "版本影响", icon: GitBranch },
  { href: "/opportunities", label: "机会", icon: Target },
  { href: "/action-briefs", label: "行动简报", icon: Rocket },
] as const;
