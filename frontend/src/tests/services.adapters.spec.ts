import { describe, expect, it } from "vitest";
import { adaptSessionStatus } from "@/utils/adapters";

describe("adaptSessionStatus", () => {
  it("maps backend session status into dashboard model", () => {
    const result = adaptSessionStatus({
      status: "running",
      room_id: 123,
      can_start: false,
      can_stop: true,
      like_multiple: 200,
    });

    expect(result.roomId).toBe("123");
    expect(result.status).toBe("running");
    expect(result.canStart).toBe(false);
    expect(result.canStop).toBe(true);
    expect(result.likeMultiple).toBe(200);
  });
});
