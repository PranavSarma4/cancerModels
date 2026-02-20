# Proteosurf — Windsurf for Biology

1,600 people die of cancer every day. KRAS was "undruggable" for 40 years until a chemical biologist at UCSF stared at atomic structures and found a hidden pocket in the GDP-bound Switch-II region. That discovery became sotorasib — the first KRAS inhibitor ever approved.

**Proteosurf gives that power to anyone with a browser.** Chat in natural language to fetch protein structures, find binding pockets, map drug contacts, dock small molecules, explore AlphaFold models, hear voice narrations, track experiments, search literature, and connect drug targets to pharma markets.

![MCP](https://img.shields.io/badge/MCP-FastMCP-brightgreen) ![Python](https://img.shields.io/badge/python-3.10+-blue) ![React](https://img.shields.io/badge/react-18-61dafb) ![License](https://img.shields.io/badge/license-MIT-gray)

---

## Sponsor Integrations

Proteosurf integrates **7 sponsor technologies** for a complete structural biology workflow:

| Sponsor | Integration | What It Does |
|---------|-------------|--------------|
| **Claude Agent SDK** | `claude_agent.py` | Native MCP tool orchestration with `@tool` decorator and `ClaudeSDKClient` — all 25 tools registered as in-process MCP tools |
| **ElevenLabs** | `voice.py` | Converts protein analysis into natural-sounding voice narration via streaming TTS. Play audio inline in the chat |
| **Databricks** | `databricks_analytics.py` | MLflow experiment tracking for docking runs and protein analyses. Query historical results to compare binding affinities |
| **NVIDIA Nemotron** | `nemotron.py` | Protein literature summarization and structure comparison using Nemotron-70B via NVIDIA's OpenAI-compatible API |
| **TrueMarket API** | `market_intel.py` | Pharma market intelligence — connects drug targets to companies, pipelines, and market data |
| **Nia by Nozomio** | `nia_search.py` | Searches research papers, bioinformatics docs, and code references to enrich AI responses with citations |
| **Mol\*** | `MolstarViewer.tsx` | Browser-native 3D protein visualization — structures auto-load when mentioned in conversation |

---

## Architecture

```
┌──────────────────┐   WebSocket /chat    ┌────────────────────────────────────┐
│  React Frontend  │◄────────────────────►│  FastAPI Backend                   │
│                  │                      │                                    │
│  Mol* 3D viewer  │   REST /api/pdb/:id  │  ProteoAgent (Claude orchestrator) │
│  Chat + audio    │◄────────────────────►│  ┌──────────────────────────────┐  │
│  Tool cards      │   REST /api/narrate  │  │  25 MCP Tools               │  │
│  Landing page    │◄────────────────────►│  │                              │  │
└──────────────────┘                      │  │  Core: fetch, list, pockets  │  │
                                          │  │  ChimeraX: open, rotate, snap│  │
                                          │  │  Docking: vina, candidates   │  │
                                          │  │  Voice: narrate (ElevenLabs) │  │
                                          │  │  Track: MLflow (Databricks)  │  │
                                          │  │  Summarize: Nemotron (NVIDIA)│  │
                                          │  │  Market: pharma (TrueMarket) │  │
                                          │  │  Research: search (Nia)      │  │
                                          │  └──────────────────────────────┘  │
                                          │                                    │
                                          │  Claude Agent SDK (alt entry point)│
                                          └────────────────────────────────────┘
```

---

## All 25 Tools

### Core Structural Biology
| Tool | Description |
|------|-------------|
| `fetch_structure(pdb_id)` | Download PDB from RCSB |
| `fetch_alphafold(uniprot_id)` | Fetch AlphaFold prediction + metadata |
| `list_residues(pdb_id, chain)` | Enumerate residues with types |
| `highlight_residues(pdb_id, residues, color, chain)` | Generate ChimeraX `.cxc` script |
| `find_pockets(pdb_id, sensitivity)` | Grid-based pocket detection |
| `find_contacts(pdb_id, chain, distance, target)` | Binding contact analysis (protein-ligand, protein-protein, glycan-receptor) |

### ChimeraX Visualization
| Tool | Description |
|------|-------------|
| `open_structure(pdb_id)` | Open in headless ChimeraX + screenshot |
| `rotate_view(axis, angle)` | Rotate view + screenshot |
| `surface_view(representation, transparency)` | Switch representation |
| `mutate_residue(chain, resseq, new_residue)` | In-place mutation |
| `snapshot(width, height, transparent)` | Capture screenshot |

### Molecular Docking
| Tool | Description |
|------|-------------|
| `dock_ligand(pdb_id, smiles, center_*, box_size)` | AutoDock Vina docking |
| `generate_candidates(pocket_residues, num)` | Fragment-based molecule suggestion |

### ElevenLabs Voice
| Tool | Description |
|------|-------------|
| `narrate_analysis(text, voice_id, ...)` | Text-to-speech narration of analysis |
| `list_voices()` | List available ElevenLabs voices |

### Databricks MLflow
| Tool | Description |
|------|-------------|
| `log_docking_experiment(pdb_id, smiles, affinity, ...)` | Track docking in MLflow |
| `log_protein_analysis(pdb_id, type, summary, metrics)` | Track analysis runs |
| `query_docking_history(pdb_id, max_results)` | Query past experiments |

### NVIDIA Nemotron
| Tool | Description |
|------|-------------|
| `summarize_protein(pdb_id, context, focus)` | Scientific summary (general/drug_target/mechanism/mutations) |
| `compare_structures(pdb_id_1, pdb_id_2, ...)` | Comparative structural analysis |

### TrueMarket Pharma Intelligence
| Tool | Description |
|------|-------------|
| `pharma_market_intel(pdb_id, pocket_residues)` | Drug target → company → market data |
| `target_pipeline_report(pdb_id)` | Drug development pipeline report |

### Nia Research Search
| Tool | Description |
|------|-------------|
| `search_protein_research(query, pdb_id, top_k)` | Search literature + docs |
| `search_bioinformatics_docs(package_name, query)` | Search package documentation |
| `deep_research(query)` | Multi-step research with citations |

---

## Quick Start

### Prerequisites
- Python 3.10+, Node.js 18+
- API keys (see `.env.example`)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[all]"     # install with all sponsor integrations
cp ../.env.example .env     # fill in your API keys
source .env

proteosurf-web              # start FastAPI on :8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                 # start Vite on :5173
```

### Docker

```bash
cp .env.example .env        # fill in API keys
docker-compose up --build
# Frontend → http://localhost:3000
# Backend  → http://localhost:8000
```

---

## MCP Server (for Cursor / Claude Desktop)

```bash
cd backend && pip install -e ".[all]"
proteosurf-mcp
```

### Cursor config (`.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "proteosurf": {
      "command": "python",
      "args": ["-m", "proteosurf.mcp_server"],
      "cwd": "/path/to/proteosurf/backend"
    }
  }
}
```

### Claude Agent SDK mode
```python
from proteosurf.claude_agent import run_agent_query
result = await run_agent_query("Find druggable pockets in 1HBS")
```

---

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `ELEVENLABS_API_KEY` | For voice | ElevenLabs API key |
| `DATABRICKS_HOST` | For tracking | Databricks workspace URL |
| `DATABRICKS_TOKEN` | For tracking | Databricks personal access token |
| `NVIDIA_API_KEY` | For Nemotron | NVIDIA API key (build.nvidia.com) |
| `TRUEMARKET_API_KEY` | For market data | TrueMarket API key |
| `NIA_API_KEY` | For research | Nia API key (app.trynia.ai) |

See `.env.example` for the full list.

---

## Example Workflows

```
User: Show me KRAS G12C and find the Switch-II pocket
→ fetch_structure("4LDJ")                         # KRAS G12C GDP-bound, 1.15Å
→ find_pockets("4LDJ", sensitivity="high")        # detect the S-IIP
→ highlight_residues("4LDJ", [58,59,60,...72])     # color switch-II loop
→ summarize_protein("4LDJ", focus="drug_target")  # Nemotron explains druggability
→ loads 4LDJ in Mol* viewer

User: How does sotorasib bind KRAS?
→ fetch_structure("6OIM")                          # KRAS G12C + sotorasib co-crystal
→ find_contacts("6OIM", chain="A", target="ligand")  # maps drug-protein contacts
→ highlight_residues("6OIM", contact_residues)     # highlight binding interface
→ narrate_analysis("Sotorasib binds covalently to Cys12 in the Switch-II pocket...")

User: Find druggable pockets in EGFR and check the pharma market
→ fetch_structure("1M17")                          # EGFR kinase + erlotinib
→ find_pockets("1M17")                             # detect binding sites
→ pharma_market_intel("1M17")                      # TrueMarket pipeline data
→ search_protein_research("EGFR kinase inhibitor resistance", "1M17") # Nia literature
→ log_protein_analysis("1M17", "pocket_detection", ...) # Databricks tracking

User: Dock imatinib into BCR-ABL
→ dock_ligand("1IEP", "CC1=C(C=C(C=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C)NC4=NC=CC(=N4)C5=CN=CC=C5")
→ log_docking_experiment("1IEP", "CC1=C...", -8.7)   # MLflow tracking
→ narrate_analysis("Imatinib binds the ABL kinase domain with...")  # ElevenLabs
```

---

## Hackathon Track Targeting

| Track | How We Win |
|-------|------------|
| Best Overall Hack | Full-stack AI + biology + 7 sponsor integrations |
| Best AI Automation | ProteoAgent automates multi-step protein analysis workflows |
| Best Consumer Track | Voice narration + beautiful UI makes biology accessible |
| Best use of Claude Agent SDK | `claude_agent.py` — all 25 tools via `@tool` decorator |
| Best use of ElevenLabs | Voice narration of protein analysis with streaming TTS |
| Best use of Databricks | MLflow experiment tracking for docking campaigns |
| Best use of Nemotron | Protein summarization + structure comparison via Nemotron-70B |
| Best use of TrueMarket API | Pharma market intel linking drug targets to companies |
| Best use of Nia | Research paper search + bioinformatics docs for context |
| Best UI/UX | Dark biotech theme, Mol* 3D viewer, audio player, tool cards |
| Most Technical | Pocket detection, docking, MCP protocol, multi-model AI |
| Most Creative | Structural biology + voice + markets = unique intersection |

---

## Project Structure

```
proteosurf/
├── docker-compose.yml
├── .env.example
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── proteosurf/
│       ├── tools.py               # Core PDB/AlphaFold/pocket tools
│       ├── chimerax_session.py    # ChimeraX subprocess manager
│       ├── chimerax_tools.py      # ChimeraX MCP tools
│       ├── docking.py             # AutoDock Vina + candidate generation
│       ├── voice.py               # ElevenLabs TTS narration
│       ├── databricks_analytics.py # MLflow experiment tracking
│       ├── nemotron.py            # NVIDIA Nemotron summarization
│       ├── market_intel.py        # TrueMarket pharma intelligence
│       ├── nia_search.py          # Nia research paper search
│       ├── agent.py               # ProteoAgent (Claude orchestrator)
│       ├── claude_agent.py        # Claude Agent SDK integration
│       ├── mcp_server.py          # MCP server entry point (25 tools)
│       ├── app.py                 # FastAPI web app
│       └── run_web.py             # Uvicorn entry point
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    └── src/
        ├── App.tsx
        ├── types.ts
        ├── hooks/useChat.ts
        └── components/
            ├── ChatPanel.tsx
            ├── MolstarViewer.tsx
            ├── ToolCard.tsx
            ├── AudioPlayer.tsx
            └── LandingPage.tsx
```

## License

MIT
