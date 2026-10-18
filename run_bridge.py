"""
CLI Runner for Web AI Roblox Bridge
Run Gemini Web, ChatGPT Web, or two-stage AI collaboration directly from your command line.

Usage Examples:
    python run_bridge.py --tabs
    python run_bridge.py "Create a neon blue fire orb" --provider gemini
    python run_bridge.py "Create a floating energy crystal" --provider chatgpt
    python run_bridge.py "Build an epic meteor shower VFX" --collab
    python run_bridge.py "Make a flame trail" --context-file my_context.txt
"""

import argparse
import asyncio
import sys
from web_ai_bridge_mcp import ask_web_ai, collab_gemini_and_chatgpt, list_open_ai_tabs


async def main():
    parser = argparse.ArgumentParser(description="Web AI Roblox Bridge CLI")
    parser.add_argument("prompt", nargs="?", default="", help="Prompt or VFX description")
    parser.add_argument("--tabs", action="store_true", help="List open Gemini and ChatGPT tabs")
    parser.add_argument("--provider", choices=["gemini", "chatgpt"], default="gemini", help="AI provider (default: gemini)")
    parser.add_argument("--collab", action="store_true", help="Run 2-stage Architect + Reviewer collaboration")
    parser.add_argument("--architect", default="gemini", choices=["gemini", "chatgpt"], help="Architect AI for collab")
    parser.add_argument("--reviewer", default="chatgpt", choices=["gemini", "chatgpt"], help="Reviewer AI for collab")
    parser.add_argument("--context", default="", help="Inline Roblox Studio context string")
    parser.add_argument("--context-file", default="", help="Path to a text/luau file to send as context")
    parser.add_argument("--out", default="", help="Save the returned Luau code to a file")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout in seconds (default: 300)")
    parser.add_argument("--no-wrap", action="store_true", help="Do not wrap prompt in strict single-code-block format")

    args = parser.parse_args()

    if args.tabs:
        print(await list_open_ai_tabs())
        return

    if not args.prompt:
        parser.print_help()
        sys.exit(0)

    # Gather context
    studio_context = args.context
    if args.context_file:
        try:
            with open(args.context_file, "r", encoding="utf-8") as f:
                file_content = f.read()
            if studio_context:
                studio_context += "\n\n" + file_content
            else:
                studio_context = file_content
        except Exception as e:
            print(f"[ERROR] Failed to read context file '{args.context_file}': {e}", file=sys.stderr)
            sys.exit(1)

    print("=" * 60)
    if args.collab:
        print(f"Running Multi-AI Collaboration: Architect ({args.architect}) -> Reviewer ({args.reviewer})")
        print(f"Task: {args.prompt}")
        print("=" * 60)
        code = await collab_gemini_and_chatgpt(
            task_description=args.prompt,
            studio_context=studio_context,
            architect=args.architect,
            reviewer=args.reviewer,
            timeout_seconds=args.timeout
        )
    else:
        print(f"Querying {args.provider.upper()} Web...")
        print(f"Task: {args.prompt}")
        print("=" * 60)
        code = await ask_web_ai(
            provider=args.provider,
            prompt=args.prompt,
            studio_context=studio_context,
            wrap_for_roblox_luau=not args.no_wrap,
            timeout_seconds=args.timeout
        )

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"[SUCCESS] Saved script to {args.out}")

    print("\n[RESULTING LUAU SCRIPT]:\n")
    try:
        print(code)
    except Exception:
        print(code.encode("ascii", errors="replace").decode("ascii"))
    print("\n" + "=" * 60)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    asyncio.run(main())
