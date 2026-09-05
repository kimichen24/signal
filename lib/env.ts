import { z } from "zod";

/**
 * Typed environment validation (zod).
 *
 * Bootstrap philosophy: secret values are optional so the app boots honestly
 * in an "unconfigured" state; features that need them check presence and
 * surface a clear state instead of crashing. Model IDs and pipeline
 * thresholds are config, never hard-coded business logic (AGENTS.md §5).
 */
export const serverEnvSchema = z.object({
  NODE_ENV: z
    .enum(["development", "production", "test"])
    .default("development"),

  // Supabase — service role stays server-only (docs/ARCHITECTURE.md §9).
  NEXT_PUBLIC_SUPABASE_URL: z.string().url().optional(),
  SUPABASE_SERVICE_ROLE_KEY: z.string().min(1).optional(),
  DATABASE_URL: z.string().optional(),

  // GitHub ingestion (Prompt 01)
  GITHUB_TOKEN: z.string().optional(),
  GITHUB_REPO: z
    .string()
    .regex(/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/, 'must be "owner/repo"')
    .default("openai/codex"),

  // OpenAI (Prompt 02) — model IDs come from env, never from code.
  OPENAI_API_KEY: z.string().optional(),
  OPENAI_CLASSIFICATION_MODEL: z.string().optional(),
  OPENAI_EMBEDDING_MODEL: z.string().optional(),

  // Deterministic pipeline thresholds
  SIGNAL_ANALYSIS_VERSION: z.string().default("v0.2.0"),
  SIGNAL_MIN_CONFIDENCE: z.coerce.number().min(0).max(1).default(0.6),
  SIGNAL_MIN_CLUSTER_SIZE: z.coerce.number().int().min(1).default(5),
  SIGNAL_EMERGING_MIN_VOLUME: z.coerce.number().int().min(1).default(5),
  SIGNAL_EMERGING_MIN_GROWTH: z.coerce.number().default(0.5),

  // Public app copy
  NEXT_PUBLIC_APP_NAME: z.string().default("Signal"),
  NEXT_PUBLIC_CASE_STUDY: z.string().default("OpenAI Codex"),
});

export type ServerEnv = z.infer<typeof serverEnvSchema>;

export class EnvValidationError extends Error {
  constructor(issues: z.ZodError["issues"]) {
    const detail = issues
      .map((issue) => `${issue.path.join(".") || "(root)"}: ${issue.message}`)
      .join("; ");
    super(`Invalid environment configuration — ${detail}`);
    this.name = "EnvValidationError";
  }
}

export function parseServerEnv(source: Record<string, string | undefined>) {
  return serverEnvSchema.safeParse(source);
}

let cached: ServerEnv | null = null;

export function getServerEnv(): ServerEnv {
  if (!cached) {
    const parsed = parseServerEnv(process.env);
    if (!parsed.success) {
      throw new EnvValidationError(parsed.error.issues);
    }
    cached = parsed.data;
  }
  return cached;
}

export function isSupabaseConfigured(): boolean {
  const env = getServerEnv();
  return Boolean(env.NEXT_PUBLIC_SUPABASE_URL && env.SUPABASE_SERVICE_ROLE_KEY);
}
