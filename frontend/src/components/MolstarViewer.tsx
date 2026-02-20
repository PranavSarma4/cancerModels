import { useState } from "react";

interface Props {
  pdbId: string | null;
}

export default function MolstarViewer({ pdbId }: Props) {
  const [loaded, setLoaded] = useState(false);

  const viewerUrl = pdbId
    ? `/viewer.html?id=${pdbId}`
    : null;

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        borderRadius: "0.5rem",
        overflow: "hidden",
        background: "#111827",
      }}
    >
      {viewerUrl && (
        <iframe
          key={pdbId}
          src={viewerUrl}
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            border: "none",
            borderRadius: "0.5rem",
          }}
          onLoad={() => setLoaded(true)}
          allow="fullscreen"
          title={`3D structure of ${pdbId}`}
        />
      )}

      {pdbId && !loaded && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "rgba(17,24,39,0.8)",
            zIndex: 10,
          }}
        >
          <div className="flex items-center gap-2 bg-gray-800 rounded-lg px-4 py-2">
            <svg className="animate-spin h-4 w-4 text-bio-500" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <span className="text-sm text-gray-300">Loading {pdbId}...</span>
          </div>
        </div>
      )}

      {!pdbId && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 10,
          }}
        >
          <div style={{ fontSize: "3rem", marginBottom: "0.75rem", opacity: 0.4 }}>
            {"\u{1F9EC}"}
          </div>
          <p className="text-sm text-gray-500">No structure loaded</p>
          <p className="text-xs text-gray-600 mt-1">
            Ask about a protein to visualise it here
          </p>
        </div>
      )}

      {pdbId && loaded && (
        <div
          className="bg-gray-900/80 backdrop-blur rounded-md px-2 py-1"
          style={{ position: "absolute", top: 12, left: 12, zIndex: 20 }}
        >
          <span className="text-xs font-mono text-bio-400">{pdbId}</span>
        </div>
      )}
    </div>
  );
}
