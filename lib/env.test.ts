import { describe, expect, it } from "vitest";
import { parseServerEnv } from "./env";

describe("parseServerEnv", () => {
  it("applies safe defaults so the app boots without secrets", () => {
    const result = parseServerEnv({});
    expect(result.success).toBe(true);
    if (!result.success) return;
    expect(result.data.GITHUB_REPO).toBe("openai/codex");
    expect(result.data.NEXT_PUBLIC_APP_NAME).toBe("Signal");
    expect(result.data.NEXT_PUBLIC_CASE_STUDY).toBe("OpenAI Codex");
    expect(result.data.SIGNAL_MIN_CONFIDENCE).toBeCloseTo(0.6);
    expect(result.data.SIGNAL_EMERGING_MIN_VOLUME).toBe(5);
    expect(result.data.SIGNAL_EMERGING_MIN_GROWTH).toBeCloseTo(0.5);
  });

  it("accepts a fully configured environment", () => {
    const result = parseServerEnv({
      NEXT_PUBLIC_SUPABASE_URL: "https://example.supabase.co",
      SUPABASE_SERVICE_ROLE_KEY: "service-role-key",
      GITHUB_REPO: "openai/codex",
      OPENAI_CLASSIFICATION_MODEL: "gpt-4.1-mini",
      OPENAI_EMBEDDING_MODEL: "text-embedding-3-small",
    });
    expect(result.success).toBe(true);
  });

  it("rejects a malformed Supabase URL", () => {
    const result = parseServerEnv({ NEXT_PUBLIC_SUPABASE_URL: "not-a-url" });
    expect(result.success).toBe(false);
  });

  it("rejects a malformed repository slug", () => {
    const result = parseServerEnv({ GITHUB_REPO: "just-a-name" });
    expect(result.success).toBe(false);
  });

  it("coerces numeric thresholds from strings", () => {
    const result = parseServerEnv({ SIGNAL_MIN_CONFIDENCE: "0.75" });
    expect(result.success).toBe(true);
    if (!result.success) return;
    expect(result.data.SIGNAL_MIN_CONFIDENCE).toBeCloseTo(0.75);
  });
});
