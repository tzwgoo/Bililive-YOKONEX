import { defineStore } from "pinia";
import {
  connectBluetoothDevice as connectBluetoothDeviceRequest,
  createBluetoothWaveform as createBluetoothWaveformRequest,
  deleteBluetoothWaveform as deleteBluetoothWaveformRequest,
  disconnectBluetoothDevice as disconnectBluetoothDeviceRequest,
  duplicateBluetoothWaveform as duplicateBluetoothWaveformRequest,
  fetchBluetoothStatus,
  fetchBluetoothStudio,
  saveBluetoothRules as saveBluetoothRulesRequest,
  scanBluetoothDevices,
  updateBluetoothWaveform as updateBluetoothWaveformRequest,
} from "@/services/bluetooth";
import { adaptBluetoothStatus } from "@/utils/adapters";
import type {
  BluetoothStatusModel,
  SaveBluetoothRulesPayload,
  UpdateBluetoothWaveformPayload,
} from "@/types/bluetooth";

export const useBluetoothStore = defineStore("bluetooth", {
  state: () => ({
    status: {
      connected: false,
      message: "",
      devices: [],
      rules: [],
    } as BluetoothStatusModel,
    studio: null as Awaited<ReturnType<typeof fetchBluetoothStudio>> | null,
  }),
  actions: {
    async fetchStatus() {
      this.status = adaptBluetoothStatus(await fetchBluetoothStatus());
    },
    async fetchStudio() {
      this.studio = await fetchBluetoothStudio();
    },
    async saveRules(payload: SaveBluetoothRulesPayload) {
      const response = await saveBluetoothRulesRequest(payload);
      if (this.studio) {
        this.studio = {
          ...this.studio,
          rule_groups: response.rule_groups,
        };
      }
      return response;
    },
    async createWaveform(name: string) {
      const response = await createBluetoothWaveformRequest(name);
      if (this.studio) {
        this.studio = {
          ...this.studio,
          waveforms: response.waveforms,
        };
      }
      return response;
    },
    async duplicateWaveform(waveformId: string, name: string) {
      const response = await duplicateBluetoothWaveformRequest(waveformId, name);
      if (this.studio) {
        this.studio = {
          ...this.studio,
          waveforms: response.waveforms,
        };
      }
      return response;
    },
    async updateWaveform(waveformId: string, payload: UpdateBluetoothWaveformPayload) {
      const response = await updateBluetoothWaveformRequest(waveformId, payload);
      if (this.studio) {
        this.studio = {
          ...this.studio,
          waveforms: response.waveforms,
        };
      }
      return response;
    },
    async deleteWaveform(waveformId: string) {
      const response = await deleteBluetoothWaveformRequest(waveformId);
      if (this.studio) {
        this.studio = {
          ...this.studio,
          waveforms: response.waveforms,
        };
      }
      return response;
    },
    async scanDevices() {
      await scanBluetoothDevices();
      await this.fetchStatus();
    },
    async connectDevice(deviceId: string) {
      await connectBluetoothDeviceRequest(deviceId);
      await this.fetchStatus();
    },
    async disconnectDevice() {
      await disconnectBluetoothDeviceRequest();
      await this.fetchStatus();
    },
  },
});
