// Type definitions for @verorun/sdk-line
// Project: VeroRun LINE Mini App SDK

export const LineMiniApp: {
  baseURL: string;
  token: string | null;
  profile: Record<string, unknown> | null;
  liffId: string | null;
  init(liffId: string): Promise<this>;
  authenticate(): Promise<{ success: boolean; data: { token: string; user: Record<string, unknown> } }>;
  restoreToken(): boolean;
  logout(): void;
  close(): void;
  openWindow(url: string): void;
  sendMessages(messages: Array<Record<string, unknown>>): Promise<void>;
  getContext(): Record<string, unknown>;
  isInClient(): boolean;
  getLanguage(): string;
};

export const LineMessaging: {
  reply(channelAccessToken: string, replyToken: string, messages: Array<Record<string, unknown>>): Promise<Record<string, unknown>>;
  push(channelAccessToken: string, userId: string, messages: Array<Record<string, unknown>>): Promise<Record<string, unknown>>;
  getProfile(channelAccessToken: string, userId: string): Promise<Record<string, unknown>>;
  createTextMessage(text: string): { type: string; text: string };
  createFlexMessage(contents: Record<string, unknown>, altText?: string): { type: string; altText: string; contents: Record<string, unknown> };
};
