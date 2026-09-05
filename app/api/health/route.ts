import { NextResponse } from "next/server";
import {
  EnvValidationError,
  getServerEnv,
  isSupabaseConfigured,
} from "@/lib/env";
import { getSupabaseAdmin } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

/**
 * Server-side health check. Reports real component status —
 * ok (all good), degraded (app up, Supabase unconfigured), error (503).
 * It never fakes a healthy database.
 */
export async function GET() {
  let appName: string;
  let caseStudy: string;
  try {
    const env = getServerEnv();
    appName = env.NEXT_PUBLIC_APP_NAME;
    caseStudy = env.NEXT_PUBLIC_CASE_STUDY;
  } catch (error) {
    if (error instanceof EnvValidationError) {
      return NextResponse.json(
        {
          status: "error",
          checks: { app: "error", database: "unknown" },
          detail: error.message,
          timestamp: new Date().toISOString(),
        },
        { status: 500 }
      );
    }
    throw error;
  }

  let database: "ok" | "unconfigured" | "error" = "unconfigured";
  let databaseError: string | null = null;

  if (isSupabaseConfigured()) {
    const client = getSupabaseAdmin();
    if (!client) {
      database = "error";
      databaseError = "Supabase client unavailable";
    } else {
      try {
        const { error } = await client
          .from("issues")
          .select("id", { count: "exact", head: true });
        if (error) {
          database = "error";
          databaseError = error.message;
        } else {
          database = "ok";
        }
      } catch (e) {
        database = "error";
        databaseError =
          e instanceof Error ? e.message : "Unknown database error";
      }
    }
  }

  const status =
    database === "ok" ? "ok" : database === "error" ? "error" : "degraded";

  return NextResponse.json(
    {
      status,
      checks: { app: "ok", database },
      databaseError,
      app_name: appName,
      case_study: caseStudy,
      timestamp: new Date().toISOString(),
    },
    { status: status === "error" ? 503 : 200 }
  );
}
