import { describe, it, expect } from "vitest";
import { renderSafeMarkdown } from "../utils/markdown";

describe("renderSafeMarkdown", () => {
  it("renders bold markdown safely", () => {
    const result = renderSafeMarkdown("**Hello** World");
    expect(result).toContain("<strong>Hello</strong>");
  });

  it("sanitizes script tags", () => {
    const result = renderSafeMarkdown("<script>alert('xss')</script> **bold text**");
    expect(result).not.toContain("<script>");
    // Markdown bold should be preserved after sanitization
    expect(result).toContain("bold text");
  });

  it("renders plain text unchanged", () => {
    const result = renderSafeMarkdown("Just text");
    expect(result).toBe("<p>Just text</p>\n");
  });
});
