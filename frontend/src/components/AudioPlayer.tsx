import { useRef, useState } from "react";
import type { AudioData } from "../types";

export default function AudioPlayer({ audio }: { audio: AudioData }) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);

  function toggle() {
    if (!audioRef.current) return;
    if (playing) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
    setPlaying(!playing);
  }

  return (
    <div className="my-2 flex items-center gap-3 bg-gray-800/80 rounded-lg px-3 py-2 border border-gray-700">
      <button
        onClick={toggle}
        className="w-8 h-8 rounded-full bg-bio-600 hover:bg-bio-500 flex items-center justify-center transition-colors flex-shrink-0"
      >
        {playing ? (
          <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
            <rect x="6" y="4" width="4" height="16" />
            <rect x="14" y="4" width="4" height="16" />
          </svg>
        ) : (
          <svg className="w-4 h-4 text-white ml-0.5" fill="currentColor" viewBox="0 0 24 24">
            <polygon points="5,3 19,12 5,21" />
          </svg>
        )}
      </button>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-gray-400 truncate">
          {"\u{1F50A}"} {audio.caption || "Voice narration"}
        </p>
        <p className="text-[10px] text-gray-600">Powered by ElevenLabs</p>
      </div>
      <audio
        ref={audioRef}
        src={`data:audio/mpeg;base64,${audio.base64}`}
        onEnded={() => setPlaying(false)}
      />
    </div>
  );
}
