import { describe, expect, it } from "vitest";
import taxonomy from "../../config/taxonomy.json";
import {
  ACTION_TYPES,
  CATEGORIES,
  ISSUE_TYPES,
  PLATFORMS,
  PRODUCT_SCOPES,
  SEVERITIES,
  SURFACES,
  TAXONOMY_VERSION,
} from "./taxonomy";

describe("taxonomy mirror", () => {
  it("keeps lib/types/taxonomy.ts in sync with config/taxonomy.json", () => {
    expect([...ISSUE_TYPES]).toEqual(taxonomy.issue_types);
    expect([...PRODUCT_SCOPES]).toEqual(taxonomy.product_scopes);
    expect([...CATEGORIES]).toEqual(taxonomy.categories);
    expect([...SURFACES]).toEqual(taxonomy.surfaces);
    expect([...PLATFORMS]).toEqual(taxonomy.platforms);
    expect([...SEVERITIES]).toEqual(taxonomy.severities);
    expect([...ACTION_TYPES]).toEqual(taxonomy.action_types);
  });

  it("pins the taxonomy version", () => {
    expect(taxonomy.version).toBe(TAXONOMY_VERSION);
  });
});
