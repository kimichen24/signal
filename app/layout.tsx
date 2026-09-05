import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";
import { AppSidebar } from "@/components/app-sidebar";
import { MobileNav } from "@/components/mobile-nav";

export const metadata: Metadata = {
  title: {
    default: "Signal — AI Product Ops Intelligence",
    template: "%s — Signal",
  },
  description:
    "Turns large volumes of unstructured user feedback into evidence-backed product signals: clusters, trends, release impact and investigation priority.",
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
