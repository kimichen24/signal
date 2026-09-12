"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_ITEMS } from "@/components/nav-items";
import { cn } from "@/lib/utils";

const primary = NAV_ITEMS[0]; // 总览
const analysis = NAV_ITEMS.slice(1, 4); // 反馈、洞察、版本影响
const decision = NAV_ITEMS.slice(4); // 机会、行动简报

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
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex items-center rounded-md px-3 py-1.5 text-[13px] transition-colors",
              active
                ? "border-l-2 border-primary bg-primary/5 font-medium text-foreground"
                : "border-l-2 border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
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
  const primaryActive =
    pathname === primary.href || pathname.startsWith(primary.href + "/");

  return (
    <aside className="sticky top-0 hidden h-svh w-56 shrink-0 flex-col border-r md:flex">
      <div className="px-5 pb-5 pt-7">
        <Link
          href="/overview"
          className="text-base font-semibold tracking-tight text-foreground"
        >
          {appName}
        </Link>
        <p className="mt-0.5 text-xs tracking-wide text-muted-foreground">
          AI 产品运营智能系统
        </p>
      </div>
      <nav className="flex-1 space-y-5 px-3">
        <div>
          <Link
            href={primary.href}
            className={cn(
              "flex items-center rounded-md px-3 py-1.5 text-[13px] transition-colors",
              primaryActive
                ? "border-l-2 border-primary bg-primary/5 font-medium text-foreground"
                : "border-l-2 border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            {primary.label}
          </Link>
        </div>
        <div className="space-y-0.5 border-t border-border pt-4">
          <p className="px-3 pb-1.5 text-[11px] tracking-wider text-muted-foreground/70">
            分析深度
          </p>
          <NavGroup items={analysis} pathname={pathname} />
        </div>
        <div className="space-y-0.5 border-t border-border pt-4">
          <p className="px-3 pb-1.5 text-[11px] tracking-wider text-muted-foreground/70">
            决策支持
          </p>
          <NavGroup items={decision} pathname={pathname} />
        </div>
      </nav>
      <div className="border-t px-5 py-5 text-xs text-muted-foreground">
        <p>案例：{caseStudy}</p>
        <p className="mt-0.5">冻结数据集 · codex-14d-2026-09-06</p>
      </div>
    </aside>
  );
}
