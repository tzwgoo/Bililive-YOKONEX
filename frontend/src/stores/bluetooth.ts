import { defineStore } from "pinia";
import {
  connectBluetoothDevice as connectBluetoothDeviceRequest,
  disconnectBluetoothDevice as disconnectBluetoothDeviceRequest,
  fetchBluetoothStatus,
  fetchBluetoothStudio,
  scanBluetoothDevices,
} from "@/services/bluetooth";
import { adaptBluetoothStatus } from "@/utils/adapters";
import type { BluetoothStatusModel } from "@/types/bluetooth";

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
