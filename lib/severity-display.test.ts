import { describe, expect, it } from "vitest";
import { formatClusterSeverity } from "./severity-display";

describe("formatClusterSeverity", () => {
  it.each([
    [0.25, "0.25"],
    [0.5, "0.50"],
    [0.75, "0.75"],
    [1, "1.00"],
    [0.812, "0.81"],
  ])("displays normalized score %s without assigning a severity level", (score, value) => {
    expect(formatClusterSeverity(score as number)).toBe(`簇平均 AI 严重度：${value} / 1`);
  });

  it.each([null, undefined])("preserves unknown score %s without inventing a low severity", (score) => {
    expect(formatClusterSeverity(score)).toBe("簇平均 AI 严重度：—");
  });
});
