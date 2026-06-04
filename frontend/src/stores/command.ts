import { defineStore } from "pinia";
import {
  connectCommand as connectCommandRequest,
  disconnectCommand as disconnectCommandRequest,
  fetchCommandStatus,
  fetchCommandStudio,
  saveCommandStudio as saveCommandStudioRequest,
} from "@/services/command";
import { adaptCommandStatus } from "@/utils/adapters";
import type { CommandConnectPayload, CommandStatusModel, UpdateCommandStudioPayload } from "@/types/command";

export const useCommandStore = defineStore("command", {
  state: () => ({
    status: {
      status: "idle",
      message: "",
      uid: "",
      userId: "",
      lastLoginAt: 0,
      canConnect: true,
      canDisconnect: false,
    } as CommandStatusModel,
    studio: null as Awaited<ReturnType<typeof fetchCommandStudio>> | null,
  }),
  actions: {
    async fetchStatus() {
      this.status = adaptCommandStatus(await fetchCommandStatus());
    },
    async fetchStudio() {
      this.studio = await fetchCommandStudio();
    },
    async saveStudio(payload: UpdateCommandStudioPayload) {
      this.studio = await saveCommandStudioRequest(payload);
    },
    async connectCommand(payload: CommandConnectPayload) {
      await connectCommandRequest(payload);
      await this.fetchStatus();
    },
    async disconnectCommand() {
      await disconnectCommandRequest();
      await this.fetchStatus();
    },
  },
});
