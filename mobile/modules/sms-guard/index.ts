import { NativeModule, requireOptionalNativeModule } from 'expo-modules-core';

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH';

export type CheckEntry = {
  sender: string;
  body: string;
  level: RiskLevel;
  score: number;
  scamType: string;
  summary: string;
  text: string;
  guardianAlerted: boolean;
  at: number;
};

export type GuardConfig = {
  serverUrl: string;
  owner: string;
  enabled: boolean;
};

type Events = { onVerdict: (event: { entry: string }) => void };

declare class SmsGuardModule extends NativeModule<Events> {
  isAccessGranted(): boolean;
  openAccessSettings(): void;
  getConfig(): GuardConfig;
  setConfig(serverUrl: string, owner: string, enabled: boolean): void;
  getHistory(): string;
  clearHistory(): void;
  testCheck(sender: string, body: string): Promise<string>;
}

/** null on iOS/web, where apps can't read incoming texts. */
const native = requireOptionalNativeModule<SmsGuardModule>('SmsGuard');

export const isSupported = native != null;

export const SmsGuard = {
  isAccessGranted: () => native?.isAccessGranted() ?? false,
  openAccessSettings: () => native?.openAccessSettings(),
  getConfig: (): GuardConfig =>
    native?.getConfig() ?? { serverUrl: '', owner: '', enabled: true },
  setConfig: (c: GuardConfig) => native?.setConfig(c.serverUrl, c.owner, c.enabled),
  getHistory: (): CheckEntry[] => JSON.parse(native?.getHistory() ?? '[]'),
  clearHistory: () => native?.clearHistory(),
  testCheck: async (sender: string, body: string): Promise<CheckEntry> => {
    if (!native) throw new Error('Automatic checks are only available on Android');
    return JSON.parse(await native.testCheck(sender, body));
  },
  onVerdict: (cb: (entry: CheckEntry) => void) =>
    native?.addListener('onVerdict', (e) => cb(JSON.parse(e.entry))),
};
