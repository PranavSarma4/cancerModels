interface Props {
  onEnter: () => void;
}

const FEATURES = [
  { icon: "\u{1F9EC}", title: "Structure Retrieval", desc: "Fetch from RCSB PDB & AlphaFold DB instantly" },
  { icon: "\u{1F573}\u{FE0F}", title: "Pocket Detection", desc: "Geometry-based binding site identification" },
  { icon: "\u{1F489}", title: "Molecular Docking", desc: "AutoDock Vina integration with RDKit prep" },
  { icon: "\u{1F3A8}", title: "ChimeraX Viz", desc: "Headless rendering and scripted visualisation" },
  { icon: "\u{1F916}", title: "AI-Powered", desc: "Claude reasons about your biology questions" },
  { icon: "\u{1F30D}", title: "3D in Browser", desc: "Mol* viewer for interactive exploration" },
];

const SPONSORS = [
  { name: "Claude Agent SDK", color: "text-orange-400 border-orange-800", desc: "Native MCP tool orchestration" },
  { name: "ElevenLabs", color: "text-purple-400 border-purple-800", desc: "Voice narration of protein analysis" },
  { name: "Databricks", color: "text-red-400 border-red-800", desc: "MLflow experiment tracking for docking" },
  { name: "NVIDIA Nemotron", color: "text-green-400 border-green-800", desc: "Protein literature summarization" },
  { name: "TrueMarket API", color: "text-blue-400 border-blue-800", desc: "Pharma market intelligence" },
  { name: "Nia by Nozomio", color: "text-amber-400 border-amber-800", desc: "Research paper & docs search" },
];

export default function LandingPage({ onEnter }: Props) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6 py-12 bg-gradient-to-b from-gray-950 via-gray-900 to-gray-950">
      <div className="text-center max-w-2xl mb-12">
        <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-bio-500 to-bio-800 flex items-center justify-center text-4xl shadow-lg shadow-bio-900/50">
          {"\u{1F9EC}"}
        </div>
        <h1 className="text-4xl sm:text-5xl font-bold mb-4 bg-gradient-to-r from-bio-400 to-bio-200 bg-clip-text text-transparent">
          Proteosurf
        </h1>
        <p className="text-lg text-gray-400 mb-2">AI-powered structural biology assistant</p>
        <p className="text-sm text-gray-500 max-w-lg mx-auto mb-8">
          Chat with an AI that fetches protein structures, detects binding pockets,
          docks ligands, narrates findings with natural voice, tracks experiments,
          and connects drug targets to pharma markets.
        </p>
        <button
          onClick={onEnter}
          className="px-8 py-3 bg-bio-600 hover:bg-bio-500 rounded-xl text-white font-semibold text-base transition-all hover:shadow-lg hover:shadow-bio-600/25 active:scale-95"
        >
          Try it
        </button>
      </div>

      {/* Features */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 max-w-4xl w-full mb-12">
        {FEATURES.map((f) => (
          <div key={f.title} className="border border-gray-800 rounded-xl px-5 py-4 bg-gray-900/50 hover:border-bio-800 transition-colors">
            <div className="text-2xl mb-2">{f.icon}</div>
            <h3 className="text-sm font-semibold mb-1">{f.title}</h3>
            <p className="text-xs text-gray-500">{f.desc}</p>
          </div>
        ))}
      </div>

      {/* Sponsor integrations */}
      <div className="max-w-4xl w-full mb-12">
        <h2 className="text-center text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Powered By
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {SPONSORS.map((s) => (
            <div key={s.name} className={`border rounded-lg px-3 py-2 text-center bg-gray-900/40 ${s.color}`}>
              <p className="text-[11px] font-semibold">{s.name}</p>
              <p className="text-[9px] text-gray-500 mt-0.5">{s.desc}</p>
            </div>
          ))}
        </div>
      </div>

      <p className="text-xs text-gray-600">
        Built with FastMCP &middot; Claude &middot; Mol* &middot; ChimeraX &middot; AutoDock Vina
      </p>
    </div>
  );
}
