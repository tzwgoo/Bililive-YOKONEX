import { defineStore } from "pinia";
import { adaptSessionStatus } from "@/utils/adapters";
import { fetchSessionStatus, startSession as startSessionRequest, stopSession as stopSessionRequest } from "@/services/session";
import type { SessionStartPayload, SessionStatusModel } from "@/types/session";

function createDefaultSessionStatus(): SessionStatusModel {
  return adaptSessionStatus({ status: "idle" });
}

export const useSessionStore = defineStore("session", {
  state: () => ({
    status: createDefaultSessionStatus(),
  }),
  actions: {
    async fetchStatus() {
      this.status = adaptSessionStatus(await fetchSessionStatus());
    },
    async startSession(payload: SessionStartPayload) {
      await startSessionRequest(payload);
      await this.fetchStatus();
    },
    async stopSession() {
      await stopSessionRequest();
      await this.fetchStatus();
    },
  },
});
