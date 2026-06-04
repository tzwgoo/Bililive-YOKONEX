import { describe, expect, it } from "vitest";
import router from "@/router";

describe("router", () => {
  it("renders dashboard route at slash", () => {
    const result = router.resolve("/");

    expect(result.name).toBe("dashboard");
    expect(result.matched).toHaveLength(1);
  });

  it("registers studio routes", () => {
    expect(router.resolve("/bluetooth/studio").name).toBe("bluetooth-studio");
    expect(router.resolve("/command/studio").name).toBe("command-studio");
  });
});
