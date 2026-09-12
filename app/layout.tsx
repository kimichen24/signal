import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";
import { AppSidebar } from "@/components/app-sidebar";
import { MobileNav } from "@/components/mobile-nav";

export const metadata: Metadata = {
  title: {
    default: "Signal｜AI 产品运营智能系统",
    template: "%s — Signal",
  },
  description:
    "将海量非结构化用户反馈，转化为可追溯、可解释、可执行的产品运营洞察。",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const appName = process.env.NEXT_PUBLIC_APP_NAME ?? "Signal";
  const caseStudy = process.env.NEXT_PUBLIC_CASE_STUDY ?? "OpenAI Codex";

  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <body className="min-h-svh font-sans antialiased">
        <div className="flex min-h-svh">
          <AppSidebar appName={appName} caseStudy={caseStudy} />
          <div className="flex min-w-0 flex-1 flex-col">
            <MobileNav appName={appName} />
            <main className="flex-1 px-6 py-8 md:px-10 md:py-12">
              <div className="mx-auto w-full max-w-4xl">{children}</div>
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
