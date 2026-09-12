import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { getServerEnv, isSupabaseConfigured } from "@/lib/env";

let cachedClient: SupabaseClient | null = null;

/**
 * Public portfolio Supabase client. Uses the anon key with RLS SELECT-only
 * policies — least-privilege for the read-only Next.js portfolio UI.
 * Returns null when Supabase is not configured so pages can render an
 * honest "not configured" state instead of crashing.
 *
 * The service_role key is reserved for the local Python pipeline
 * (pipeline/supabase_client.py) and is never used by this Next.js client.
 */
export function getSupabaseAdmin(): SupabaseClient | null {
  if (!isSupabaseConfigured()) return null;
  if (!cachedClient) {
    const env = getServerEnv();
    const anonKey = env.SUPABASE_ANON_KEY;
    if (!anonKey) return null;
    cachedClient = createClient(
      env.NEXT_PUBLIC_SUPABASE_URL!,
      anonKey,
      {
        auth: { persistSession: false, autoRefreshToken: false },
      }
    );
  }
  return cachedClient;
}
