import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

describe("app shell layout", () => {
  it("keeps the desktop sidebar fixed and offsets the main content", () => {
    const css = readFileSync(resolve(__dirname, "../styles/app.css"), "utf-8").replace(/\r\n/g, "\n");

    expect(css).toContain(".app-sidebar {\n  position: fixed;");
    expect(css).toContain("width: 260px;");
    expect(css).toContain(".app-main {\n  min-width: 0;\n  margin-left: 260px;");
    expect(css).toContain("@media (max-width: 720px) {");
    expect(css).toContain(".app-sidebar {\n    position: static;");
    expect(css).toContain(".app-main {\n    margin-left: 0;");
  });
});
