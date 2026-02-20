import { useState } from "react";
import LandingPage from "./components/LandingPage";
import ChatPanel from "./components/ChatPanel";
import MolstarViewer from "./components/MolstarViewer";
import { useChat } from "./hooks/useChat";

export default function App() {
  const [showApp, setShowApp] = useState(false);
  const { messages, status, isStreaming, send, activePdb } = useChat();

  if (!showApp) {
    return <LandingPage onEnter={() => setShowApp(true)} />;
  }

  return (
    <div className="flex" style={{ height: "100vh", overflow: "hidden" }}>
      {/* Chat panel — left */}
      <div className="w-[420px] min-w-[340px] border-r border-gray-800 flex-shrink-0" style={{ height: "100vh" }}>
        <ChatPanel
          messages={messages}
          status={status}
          isStreaming={isStreaming}
          onSend={send}
        />
      </div>

      {/* 3D viewer — right */}
      <div style={{ flex: 1, height: "100vh", padding: "12px", boxSizing: "border-box" }}>
        <MolstarViewer pdbId={activePdb} />
      </div>
    </div>
  );
}
