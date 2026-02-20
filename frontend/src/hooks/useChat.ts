import { useState, useCallback, useRef, useEffect } from "react";
import type {
  ChatMessage,
  ConnectionStatus,
  ToolResult,
  ImageData,
  AudioData,
  WSMessage,
} from "../types";

let _nextId = 0;
const uid = () => `msg-${++_nextId}-${Date.now()}`;

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [isStreaming, setIsStreaming] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const pendingRef = useRef<{
    text: string;
    tools: ToolResult[];
    images: ImageData[];
    audio: AudioData[];
  }>({ text: "", tools: [], images: [], audio: [] });

  const [activePdb, setActivePdb] = useState<string | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    setStatus("connecting");

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${window.location.host}/chat`);
    wsRef.current = ws;

    ws.onopen = () => setStatus("connected");
    ws.onclose = () => {
      setStatus("disconnected");
      wsRef.current = null;
    };
    ws.onerror = () => setStatus("disconnected");

    ws.onmessage = (ev) => {
      const msg: WSMessage = JSON.parse(ev.data);

      switch (msg.type) {
        case "text":
          pendingRef.current.text += msg.text ?? "";
          flushPending();
          break;

        case "tool": {
          const toolName = msg.tool_name ?? "unknown";
          const toolInput = msg.tool_input ?? {};
          const toolResult = msg.result ?? "";

          const existing = pendingRef.current.tools.find(
            (t) => t.tool_name === toolName && !t.result
          );
          if (existing && toolResult) {
            existing.result = toolResult;
          } else if (!existing) {
            pendingRef.current.tools.push({
              tool_name: toolName,
              tool_input: toolInput,
              result: toolResult,
              collapsed: true,
            });
          }

          if (toolResult) {
            const pdbMatch =
              (toolInput as Record<string, string>)?.pdb_id ??
              toolResult.match(/"pdb_id":\s*"([^"]+)"/)?.[1];
            if (pdbMatch && /^[A-Z0-9]{4}$/i.test(String(pdbMatch))) {
              setActivePdb(String(pdbMatch).toUpperCase());
            }
          }
          flushPending();
          break;
        }

        case "image":
          if (msg.base64) {
            pendingRef.current.images.push({
              base64: msg.base64,
              caption: msg.caption ?? "",
            });
            flushPending();
          }
          break;

        case "audio":
          if (msg.base64) {
            pendingRef.current.audio.push({
              base64: msg.base64,
              caption: msg.caption ?? "",
            });
            flushPending();
          }
          break;

        case "done":
          setIsStreaming(false);
          break;

        case "error":
          setMessages((prev) => [
            ...prev,
            { id: uid(), role: "system", content: msg.text ?? "Unknown error", timestamp: Date.now() },
          ]);
          setIsStreaming(false);
          break;

        case "system":
          setMessages((prev) => [
            ...prev,
            { id: uid(), role: "system", content: msg.text ?? "", timestamp: Date.now() },
          ]);
          break;
      }
    };
  }, []);

  function flushPending() {
    const p = pendingRef.current;
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last?.role === "assistant" && last.id.startsWith("stream-")) {
        return [
          ...prev.slice(0, -1),
          { ...last, content: p.text, tools: [...p.tools], images: [...p.images], audio: [...p.audio] },
        ];
      }
      return [
        ...prev,
        {
          id: `stream-${Date.now()}`,
          role: "assistant",
          content: p.text,
          tools: [...p.tools],
          images: [...p.images],
          audio: [...p.audio],
          timestamp: Date.now(),
        },
      ];
    });
  }

  const send = useCallback(
    (text: string) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        connect();
        setTimeout(() => send(text), 500);
        return;
      }
      pendingRef.current = { text: "", tools: [], images: [], audio: [] };
      setMessages((prev) => [
        ...prev,
        { id: uid(), role: "user", content: text, timestamp: Date.now() },
      ]);
      setIsStreaming(true);
      wsRef.current.send(JSON.stringify({ message: text }));
    },
    [connect],
  );

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  return { messages, status, isStreaming, send, activePdb, connect };
}
