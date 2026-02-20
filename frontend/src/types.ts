export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  tools?: ToolResult[];
  images?: ImageData[];
  audio?: AudioData[];
  timestamp: number;
}

export interface ToolResult {
  tool_name: string;
  tool_input: Record<string, unknown>;
  result: string;
  collapsed: boolean;
}

export interface ImageData {
  base64: string;
  caption: string;
}

export interface AudioData {
  base64: string;
  caption: string;
}

export type ConnectionStatus = "disconnected" | "connecting" | "connected";

export interface WSMessage {
  type: "text" | "tool" | "image" | "audio" | "done" | "error" | "system";
  text?: string;
  tool_name?: string;
  tool_input?: Record<string, unknown>;
  result?: string;
  base64?: string;
  caption?: string;
}
