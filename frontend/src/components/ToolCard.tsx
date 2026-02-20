import { useState } from "react";
import type { ToolResult } from "../types";

const TOOL_ICONS: Record<string, string> = {
  fetch_structure: "\u{1F9EC}",
  fetch_alphafold: "\u{1F52C}",
  list_residues: "\u{1F9EA}",
  highlight_residues: "\u{1F3A8}",
  find_pockets: "\u{1F573}\u{FE0F}",
  find_contacts: "\u{1F91D}",
  open_structure: "\u{1F4C2}",
  rotate_view: "\u{1F504}",
  surface_view: "\u{1F30D}",
  mutate_residue: "\u{1F9EC}",
  snapshot: "\u{1F4F8}",
  dock_ligand: "\u{1F489}",
  generate_candidates: "\u{1F48A}",
  narrate_analysis: "\u{1F50A}",
  list_voices: "\u{1F399}\u{FE0F}",
  log_docking_experiment: "\u{1F4CA}",
  log_protein_analysis: "\u{1F4CA}",
  query_docking_history: "\u{1F4C8}",
  summarize_protein: "\u{1F9E0}",
  compare_structures: "\u{1F504}",
  pharma_market_intel: "\u{1F4B0}",
  target_pipeline_report: "\u{1F4C4}",
  search_protein_research: "\u{1F50D}",
  search_bioinformatics_docs: "\u{1F4DA}",
  deep_research: "\u{1F9D0}",
};

const SPONSOR_BADGE: Record<string, string> = {
  narrate_analysis: "ElevenLabs",
  list_voices: "ElevenLabs",
  log_docking_experiment: "Databricks",
  log_protein_analysis: "Databricks",
  query_docking_history: "Databricks",
  summarize_protein: "Nemotron",
  compare_structures: "Nemotron",
  pharma_market_intel: "TrueMarket",
  target_pipeline_report: "TrueMarket",
  search_protein_research: "Nia",
  search_bioinformatics_docs: "Nia",
  deep_research: "Nia",
};

const BADGE_COLORS: Record<string, string> = {
  ElevenLabs: "bg-purple-900/50 text-purple-300 border-purple-700",
  Databricks: "bg-red-900/50 text-red-300 border-red-700",
  Nemotron: "bg-green-900/50 text-green-300 border-green-700",
  TrueMarket: "bg-blue-900/50 text-blue-300 border-blue-700",
  Nia: "bg-amber-900/50 text-amber-300 border-amber-700",
};

export default function ToolCard({ tool }: { tool: ToolResult }) {
  const [open, setOpen] = useState(false);
  const icon = TOOL_ICONS[tool.tool_name] ?? "\u{1F527}";
  const badge = SPONSOR_BADGE[tool.tool_name];
  const inputStr = JSON.stringify(tool.tool_input, null, 2);
  const isRunning = !tool.result;

  return (
    <div className={`my-2 rounded-lg border overflow-hidden ${isRunning ? "border-bio-700 bg-bio-900/20" : "border-gray-700 bg-gray-800/60"}`}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-gray-700/40 transition-colors"
      >
        {isRunning ? (
          <svg className="animate-spin h-4 w-4 text-bio-500 flex-shrink-0" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        ) : (
          <span className="text-base">{icon}</span>
        )}
        <span className={`font-medium ${isRunning ? "text-bio-300" : "text-bio-400"}`}>{tool.tool_name}</span>
        {badge && (
          <span className={`text-[9px] px-1.5 py-0.5 rounded border font-medium ${BADGE_COLORS[badge] ?? ""}`}>
            {badge}
          </span>
        )}
        <span className="text-gray-500 text-xs truncate flex-1">
          {isRunning
            ? "running..."
            : Object.entries(tool.tool_input)
                .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
                .join(", ")
                .slice(0, 60)}
        </span>
        {!isRunning && (
          <svg
            className={`w-4 h-4 text-gray-500 transition-transform ${open ? "rotate-180" : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        )}
      </button>
      {open && !isRunning && (
        <div className="px-3 pb-3 border-t border-gray-700">
          <div className="mt-2">
            <p className="text-xs text-gray-500 mb-1">Input</p>
            <pre className="text-xs bg-gray-900 rounded p-2 overflow-x-auto text-gray-300 font-mono">
              {inputStr}
            </pre>
          </div>
          {tool.result && (
            <div className="mt-2">
              <p className="text-xs text-gray-500 mb-1">Result</p>
              <pre className="text-xs bg-gray-900 rounded p-2 overflow-x-auto text-gray-300 font-mono max-h-64 overflow-y-auto">
                {tool.result}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
