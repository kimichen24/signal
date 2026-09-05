import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { getServerEnv, isSupabaseConfigured } from "@/lib/env";

let cachedClient: SupabaseClient | null = null;

/**
 * Service-role Supabase client for server-side code only (Server Components,
 * route handlers, server actions). Returns null when Supabase is not
 * configured so pages can render an honest "not configured" state instead of
 * crashing. Never import this from client components.
 */
export function getSupabaseAdmin(): SupabaseClient | null {
  if (!isSupabaseConfigured()) return null;
  if (!cachedClient) {
    const env = getServerEnv();
    cachedClient = createClient(
      env.NEXT_PUBLIC_SUPABASE_URL!,
      env.SUPABASE_SERVICE_ROLE_KEY!,
      {
        auth: { persistSession: false, autoRefreshToken: false },
      }
    );
  }
  return cachedClient;
}
