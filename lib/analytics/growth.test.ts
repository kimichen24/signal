import { describe, expect, it } from "vitest";
import { computeGrowth } from "./growth";

const thresholds = { minVolume: 5, minGrowth: 0.5 };

describe("computeGrowth", () => {
  it("computes growth rate with the PRD formula", () => {
    expect(computeGrowth(10, 5, thresholds).growthRate).toBeCloseTo(1);
    expect(computeGrowth(6, 6, thresholds).growthRate).toBeCloseTo(0);
    expect(computeGrowth(2, 10, thresholds).growthRate).toBeCloseTo(-0.8);
  });

  it("divides by one when the previous period is empty", () => {
    expect(computeGrowth(10, 0, thresholds).growthRate).toBeCloseTo(10);
  });

  it("requires the volume threshold before flagging emerging", () => {
    const result = computeGrowth(4, 1, thresholds);
    expect(result.growthRate).toBeGreaterThan(thresholds.minGrowth);
    expect(result.meetsVolumeThreshold).toBe(false);
    expect(result.isEmerging).toBe(false);
  });

  it("flags emerging only above both thresholds", () => {
    expect(computeGrowth(10, 5, thresholds).isEmerging).toBe(true);
    expect(computeGrowth(7, 5, thresholds).isEmerging).toBe(false); // growth 0.4 < 0.5
    expect(computeGrowth(2, 0, thresholds).isEmerging).toBe(false);
  });

  it("rejects negative counts", () => {
    expect(() => computeGrowth(-1, 0, thresholds)).toThrow(RangeError);
  });
});
