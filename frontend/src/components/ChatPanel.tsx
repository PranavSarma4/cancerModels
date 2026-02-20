import { useState, useRef, useEffect } from "react";
import type { ChatMessage, ConnectionStatus } from "../types";
import ToolCard from "./ToolCard";
import AudioPlayer from "./AudioPlayer";

interface Props {
  messages: ChatMessage[];
  status: ConnectionStatus;
  isStreaming: boolean;
  onSend: (text: string) => void;
}

const STATUS_COLORS: Record<ConnectionStatus, string> = {
  connected: "bg-bio-500",
  connecting: "bg-yellow-500",
  disconnected: "bg-red-500",
};

const EXAMPLES = [
  "Show me KRAS G12C bound to sotorasib (6OIM) and highlight the Switch-II pocket",
  "Find druggable pockets in the EGFR kinase domain (1M17) — which ones could bind a small molecule?",
  "Fetch the AlphaFold model for human BCL-2 (Q07817) and explain its role in apoptosis",
  "Show me a glycoprotein binding Siglec-7 (2HRL) — highlight every sialic-acid contact residue",
  "Compare wild-type p53 (2XWR) with a cancer hotspot mutant — what changes in the DNA-binding surface?",
  "Dock imatinib (CC1=C(C=C(C=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C)NC4=NC=CC(=N4)C5=CN=CC=C5) into BCR-ABL (1IEP)",
];

export default function ChatPanel({ messages, status, isStreaming, onSend }: Props) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setInput("");
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-bio-600 flex items-center justify-center text-lg font-bold">
            P
          </div>
          <div>
            <h1 className="text-sm font-semibold">Proteosurf</h1>
            <p className="text-[10px] text-gray-500">Structural Biology AI</p>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <div className={`w-2 h-2 rounded-full ${STATUS_COLORS[status]}`} />
          <span className="text-[10px] text-gray-500 capitalize">{status}</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center gap-6">
            <div>
              <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-bio-600 to-bio-800 flex items-center justify-center text-3xl">
                {"\u{1F9EC}"}
              </div>
              <h2 className="text-lg font-semibold mb-1">Proteosurf</h2>
              <p className="text-sm text-gray-400 max-w-sm">
                Windsurf for biology. Chat with proteins the way a mechanic dissects an engine — explore structures, find hidden pockets, dock drug candidates, and generate synthesis-ready molecules.
              </p>
            </div>
            <div className="grid grid-cols-1 gap-2 w-full max-w-sm">
              {EXAMPLES.map((ex) => (
                <button
                  key={ex}
                  onClick={() => onSend(ex)}
                  className="text-left text-xs px-3 py-2 rounded-lg border border-gray-700 hover:border-bio-600 hover:bg-gray-800/50 transition-colors text-gray-400 hover:text-gray-200"
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-xl px-4 py-2.5 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-bio-700 text-white"
                  : msg.role === "system"
                    ? "bg-yellow-900/30 text-yellow-300 border border-yellow-800/40"
                    : "bg-gray-800 text-gray-200"
              }`}
            >
              {msg.content && <div className="whitespace-pre-wrap">{msg.content}</div>}

              {msg.tools?.map((t, i) => <ToolCard key={i} tool={t} />)}

              {msg.images?.map((img, i) => (
                <div key={i} className="mt-2">
                  <img
                    src={`data:image/png;base64,${img.base64}`}
                    alt={img.caption}
                    className="rounded-lg max-w-full border border-gray-700"
                  />
                  {img.caption && (
                    <p className="text-xs text-gray-500 mt-1">{img.caption}</p>
                  )}
                </div>
              ))}

              {msg.audio?.map((a, i) => (
                <AudioPlayer key={i} audio={a} />
              ))}
            </div>
          </div>
        ))}

        {isStreaming && (
          <div className="flex justify-start">
            <div className="bg-gray-800 rounded-xl px-4 py-2.5">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-bio-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-2 h-2 bg-bio-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-2 h-2 bg-bio-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="px-4 py-3 border-t border-gray-800">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="e.g. Show me the KRAS Switch-II pocket..."
            disabled={isStreaming}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm placeholder-gray-500 focus:outline-none focus:border-bio-500 focus:ring-1 focus:ring-bio-500/30 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isStreaming || !input.trim()}
            className="px-4 py-2 bg-bio-600 hover:bg-bio-500 disabled:bg-gray-700 disabled:text-gray-500 rounded-lg text-sm font-medium transition-colors"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
