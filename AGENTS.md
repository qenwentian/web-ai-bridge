# AI Agent Instructions for this Workspace

This project is integrated with **Roblox Studio** and the **Web AI Roblox Bridge** (`web_ai_bridge_mcp.py`).
All AI agents (Antigravity, Codex, etc.) working in this repository must adhere to the following workflow when creating or modifying Roblox Luau VFX, 3D models, or gameplay scripts.

---

## Active Skills & MCP Servers

1. **`Web_AI_Roblox_Bridge` MCP Server:**
   - Command (from the repository directory): `python web_ai_bridge_mcp.py`
   - Tools available:
     - `ask_web_ai(provider: "gemini"|"chatgpt", prompt: str, studio_context: str = "", wrap_for_roblox_luau: bool = True) -> str`
     - `collab_gemini_and_chatgpt(task_description: str, studio_context: str = "", architect: str = "gemini", reviewer: str = "chatgpt") -> str`
     - `list_open_ai_tabs() -> str`
2. **`Roblox_Studio` MCP Server:**
   - Connects directly to the live Roblox Studio place.
   - Tool `execute_luau(code: str)` executes Luau code directly inside the active Studio place.
3. **CLI Runner (Alternative for non-MCP agents):**
   - `python run_bridge.py "<prompt>" --provider gemini --context "<studio_context>"`
   - `python run_bridge.py "<prompt>" --collab --context "<studio_context>"`

---

## Mandatory 4-Step Execution Workflow

Whenever the user asks to build or enhance a Roblox VFX, 3D model, or script:

1. **Step 1 — Inspect Studio Live Context First:**
   - Always check selected instances (`game:GetService("Selection"):Get()`) using Roblox Studio MCP (`execute_luau` or `selection`).
   - Extract `.Size`, `.CFrame`, `.Position`, attachments (`BladeTip`, `BladeBase`, etc.), and existing particle emitters.
   - Read any relevant workspace files if hooking into existing combat/ability systems.
2. **Step 2 — Send Context to Web AI:**
   - Format the inspection report as `studio_context` and pass it to `ask_web_ai` or `collab_gemini_and_chatgpt`.
3. **Step 3 — Execute in Studio:**
   - Inject the returned clean Luau code into Roblox Studio via `execute_luau`.
4. **Step 4 — Self-Healing Loop:**
   - If Studio returns a runtime error or syntax issue, feed the exact error and failing code back into `ask_web_ai` to patch it until execution is clean.
