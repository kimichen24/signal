"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  FileText,
  GitCompare,
  LayoutDashboard,
  MessageSquare,
  Sparkles,
  Target,
  type LucideIcon,
} from "lucide-react";
import { NAV_ITEMS } from "@/components/nav-items";
import { cn } from "@/lib/utils";

const primary = NAV_ITEMS[0]; // 总览
const observation = NAV_ITEMS.slice(1, 3); // 反馈、洞察
const decision = NAV_ITEMS.slice(3); // 版本影响、机会、行动简报

const icons: Record<string, LucideIcon> = {
  "/overview": LayoutDashboard,
  "/feedback": MessageSquare,
  "/insights": Sparkles,
  "/releases": GitCompare,
  "/opportunities": Target,
  "/action-briefs": FileText,
};

function NavGroup({
  items,
  pathname,
}: {
  items: { href: string; label: string }[];
  pathname: string;
}) {
  return (
    <>
      {items.map((item) => {
        const active =
          pathname === item.href || pathname.startsWith(item.href + "/");
        const Icon = icons[item.href];
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex h-10 items-center gap-2.5 rounded-lg px-3 text-sm transition-colors",
              active
                ? "bg-indigo-50 text-indigo-700"
                : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
            )}
          >
            <Icon
              aria-hidden="true"
              className={cn("size-4 shrink-0", active ? "text-indigo-600" : "text-muted-foreground/80")}
              strokeWidth={1.75}
            />
            {item.label}
          </Link>
        );
      })}
    </>
  );
}

export function AppSidebar({
  appName,
  caseStudy,
}: {
  appName: string;
  caseStudy: string;
}) {
  const pathname = usePathname();

  return (
    <aside className="sticky top-0 hidden h-svh w-[244px] shrink-0 flex-col border-r md:flex">
      <div className="px-5 pb-4 pt-6">
        <Link
          href="/overview"
          className="text-[23px] font-semibold leading-7 tracking-tight text-foreground"
        >
          {appName}
        </Link>
        <p className="mt-0.5 text-xs leading-4 text-muted-foreground">
          AI 产品运营智能系统
        </p>
      </div>
      <nav className="flex-1 space-y-5 px-3">
        <div>
          <NavGroup items={[primary]} pathname={pathname} />
        </div>
        <div>
          <p className="mb-1.5 px-3 text-[11px] font-medium tracking-wide text-muted-foreground">
            观察
          </p>
          <NavGroup items={observation} pathname={pathname} />
        </div>
        <div>
          <p className="mb-1.5 px-3 text-[11px] font-medium tracking-wide text-muted-foreground">
            决策
          </p>
          <NavGroup items={decision} pathname={pathname} />
        </div>
      </nav>
      <div className="mt-auto px-5 pb-5 pt-6 text-xs text-muted-foreground">
        <p>案例数据</p>
        <p className="mt-0.5">{caseStudy}</p>
      </div>
    </aside>
  );
}
