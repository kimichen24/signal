"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_ITEMS } from "@/components/nav-items";
import { cn } from "@/lib/utils";

export function AppSidebar({
  appName,
  caseStudy,
}: {
  appName: string;
  caseStudy: string;
}) {
  const pathname = usePathname();

  return (
    <aside className="sticky top-0 hidden h-svh w-60 shrink-0 flex-col border-r md:flex">
      <div className="px-6 pb-6 pt-8">
        <Link
          href="/overview"
          className="text-lg font-semibold tracking-tight"
        >
          {appName}
        </Link>
        <p className="mt-1 text-xs text-muted-foreground">
          AI Product Ops Intelligence
        </p>
      </div>
      <nav className="flex-1 space-y-1 px-3">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const active =
            pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-accent font-medium text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
              )}
            >
              <Icon className="size-4" strokeWidth={1.75} />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t px-6 py-6 text-xs text-muted-foreground">
        <p>Case Study</p>
        <p className="mt-0.5 text-foreground/80">{caseStudy}</p>
        <p className="mt-3">MVP · Real feedback only</p>
      </div>
    </aside>
  );
}
