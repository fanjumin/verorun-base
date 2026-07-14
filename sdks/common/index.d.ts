// Type definitions for @verorun/sdk-common
// Project: VeroRun Social Media Mini-Program SDK

export class VeroAuth {
  constructor(config: { baseURL: string; platform: 'douyin' | 'wechat' | 'telegram' | 'line' });
  login(credentials: Record<string, unknown>): Promise<{ success: boolean; data: { token: string; user: Record<string, unknown> } }>;
  validateToken(token: string): Promise<{ success: boolean; data: { valid: boolean; user: Record<string, unknown> } }>;
}

export class VeroChat {
  constructor(config: { baseURL: string; token: string; platform: string });
  send(message: string, history?: Array<{ role: string; content: string }>): Promise<{ success: boolean; data: { reply: string; retrievedKnowledge: unknown[] } }>;
  streamChat(
    message: string,
    history?: Array<{ role: string; content: string }>,
    onToken?: (token: string) => void,
    onDone?: (result: { reply: string; retrievedKnowledge: unknown[]; error?: string }) => void
  ): Promise<void>;
  searchKnowledge(query: string): Promise<{ success: boolean; data: unknown[] }>;
  getHistory(): Promise<{ success: boolean; data: { messages: unknown[] } }>;
}

export class VeroRAG {
  constructor(config: { baseURL: string; token: string });
  search(query: string, topK?: number, category?: string | null): Promise<{ success: boolean; data: Array<{ id: string; title: string; content: string; score: number; category: string }> }>;
  getSiteInfo(): Promise<{ success: boolean; data: Record<string, unknown> }>;
  getPages(): Promise<{ success: boolean; data: Array<{ slug: string; title: string }> }>;
  getPage(slug: string): Promise<{ success: boolean; data: { slug: string; title: string; blocks: unknown[] } }>;
}
