import { describe, expect, it } from "vitest";
import { classNames } from "@/lib/classNames";

describe("classNames", () => {
  it("joins only truthy class values", () => {
    expect(classNames("base", false, undefined, "active", null, "wide")).toBe("base active wide");
  });

  it("returns an empty string when nothing is provided", () => {
    expect(classNames(undefined, false, null)).toBe("");
  });
});
