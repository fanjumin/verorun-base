// Type definitions for @verorun/sdk-telegram
// Project: VeroRun Telegram Mini App SDK

export const TelegramBot: {
  setWebhook(botToken: string, webhookUrl: string): Promise<{ ok: boolean; description?: string }>;
  setMiniAppMenuButton(botToken: string, webappUrl: string, buttonText?: string): Promise<{ ok: boolean; description?: string }>;
  sendMessage(botToken: string, chatId: number | string, text: string, options?: {
    parseMode?: string;
    replyMarkup?: unknown;
    disablePreview?: boolean;
  }): Promise<{ ok: boolean; result?: unknown }>;
  getMe(botToken: string): Promise<{ ok: boolean; result?: { id: number; username: string } }>;
};

export const TelegramMiniApp: {
  tg: any | null;
  baseURL: string;
  token: string | null;
  user: Record<string, unknown> | null;
  init(): this;
  authenticate(): Promise<{ success: boolean; data: { token: string; user: Record<string, unknown> } }>;
  restoreToken(): boolean;
  logout(): void;
  showPopup(message: string, callback?: (buttonId: string) => void): void;
  showConfirm(message: string, callback: (confirmed: boolean) => void): void;
  showBackButton(callback: () => void): void;
  hideBackButton(): void;
  sendData(data: Record<string, unknown> | string): void;
  close(): void;
  getColorScheme(): string;
  setMainButton(text: string, onClick?: () => void, options?: {
    color?: string;
    textColor?: string;
    isActive?: boolean;
    isVisible?: boolean;
  }): void;
  hideMainButton(): void;
};
