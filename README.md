# Web AI Bridge

Ask ChatGPT and Gemini through their web interfaces from an MCP client or the command line. Web AI Bridge connects to a dedicated Chrome session using Playwright and the Chrome DevTools Protocol (CDP), sends your prompt, and reads the response.

The bridge uses your signed-in browser sessions; it does not require API keys. It started as a Roblox tool, so some names, output labels, and defaults still refer to Roblox. For general questions and coding tasks, use `--no-wrap` in the CLI or `wrap_for_roblox_luau=False` through MCP.

## Requirements

- Python 3.10 or newer
- Google Chrome
- A ChatGPT or Gemini account signed in to the dedicated browser session
- Windows for the included browser launcher; the Python bridge connects to Chrome at `http://127.0.0.1:9222`

## Setup

Clone the repository and install the Python dependencies:

```powershell
git clone https://github.com/qenwentian/web-ai-bridge.git
cd web-ai-bridge
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start the dedicated Chrome session:

```powershell
.\launch_ai_browser.bat
```

Sign in to ChatGPT and/or Gemini in the browser that opens. Keep it running while using the bridge. The launcher stores its separate profile in `%LOCALAPPDATA%\Google\Chrome\AIBridgeProfile`.

## Command line

Check the connected browser tabs:

```powershell
.venv\Scripts\python.exe run_bridge.py --tabs
```

Ask either provider a general question:

```powershell
.venv\Scripts\python.exe run_bridge.py "Explain Python generators with a short example" --provider chatgpt --no-wrap
.venv\Scripts\python.exe run_bridge.py "Suggest names for a note-taking app" --provider gemini --no-wrap
```

Include a context file and save the response:

```powershell
.venv\Scripts\python.exe run_bridge.py "Review this code and suggest improvements" --provider chatgpt --no-wrap --context-file example.py --out review.txt
```

Without `--no-wrap`, the bridge requests a single executable Roblox Luau code block and extracts code from the response:

```powershell
.venv\Scripts\python.exe run_bridge.py "Create a floating energy crystal" --provider gemini --out crystal.luau
```

Run `run_bridge.py --help` for all options. Responses have a default timeout of 300 seconds; adjust it with `--timeout`.

## MCP configuration

Use `.mcp.example.json` as a starting point for your MCP client configuration. Replace the paths with the absolute paths to your checkout and its virtual environment:

```json
{
  "mcpServers": {
    "Web_AI_Bridge": {
      "command": "C:/path/to/web-ai-bridge/.venv/Scripts/python.exe",
      "args": [
        "C:/path/to/web-ai-bridge/web_ai_bridge_mcp.py"
      ]
    }
  }
}
```

The server runs over standard input/output. The browser must be running separately.

Available tools:

| Tool | Purpose |
| --- | --- |
| `ask_web_ai` | Send a prompt to `chatgpt` or `gemini`. Set `wrap_for_roblox_luau=False` for general use. |
| `list_open_ai_tabs` | List connected browser tabs, URLs, and titles, including non-AI tabs. |
| `collab_gemini_and_chatgpt` | Generate a Roblox Luau script with one provider, then send it to another for review. |

`ask_web_ai` accepts `provider`, `prompt`, optional `studio_context`, `wrap_for_roblox_luau`, and `timeout_seconds`. The optional context is pasted into the prompt; its current heading refers to Roblox Studio even when wrapping is disabled.

The collaboration tool and CLI `--collab` mode currently always request Roblox Luau. `--no-wrap` only affects single-provider requests.

## Browser access and privacy

- CDP gives the bridge control of the dedicated browser session. Keep port 9222 local; do not expose it through a public port forward or tunnel.
- Use the dedicated profile for AI tabs. Tab listing reports every tab in that session, and requests reuse an existing provider tab and its conversation history. Open a fresh conversation when you want separate context.
- Prompts and context files are sent to the selected website. Collaboration mode also sends the first provider's output to the second provider.
- Keep browser profiles, cookies, login data, and secrets out of Git. The included `.gitignore` excludes the local `.mcp.json`, logs, environment files, virtual environments, and Python caches.

## Limitations and troubleshooting

This is browser automation. Changes to website layouts can break input detection or response extraction. Login prompts, account limits, and interrupted generations can also prevent requests from completing. Responses are detected using page elements and text stabilization, so verify returned output before relying on it.

- **Cannot connect to Chrome:** run `launch_ai_browser.bat` and keep that Chrome session open. The bridge expects port 9222.
- **Input box not found:** check that you are signed in and the provider's chat page is ready in the dedicated browser.
- **Unexpected or old response:** open a fresh chat and retry. The current extraction logic can pick up earlier messages or code blocks.
- **Concurrent requests:** send requests one at a time; the bridge does not isolate requests sharing the same provider tab.

The bridge returns text or code. It does not execute generated code in Roblox Studio. The included `AGENTS.md` and `AGENT_WORKFLOW.md` describe the original Roblox integration, which requires a separate Studio MCP connection.
