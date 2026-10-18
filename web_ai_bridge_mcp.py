"""
Web AI Roblox Bridge MCP Server
Provides autonomous browser-based integration with Gemini Web and ChatGPT Web
via Chrome DevTools Protocol (CDP) for generating and refining Roblox Luau VFX / 3D models.
"""

import asyncio
import re
import sys
from typing import Optional
from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright, Page, Browser

mcp = FastMCP("Web_AI_Roblox_Bridge")

CDP_URL = "http://127.0.0.1:9222"


async def get_or_create_page(browser: Browser, provider: str) -> Page:
    """Finds an existing tab for Gemini/ChatGPT or creates one if not found."""
    target_domain = "gemini.google.com" if provider == "gemini" else "chatgpt.com"
    fallback_url = "https://gemini.google.com/app" if provider == "gemini" else "https://chatgpt.com"

    for context in browser.contexts:
        for page in context.pages:
            if target_domain in page.url.lower():
                await page.bring_to_front()
                return page

    # If no existing tab was found, create one in the primary context
    context = browser.contexts[0] if browser.contexts else await browser.new_context()
    page = await context.new_page()
    await page.goto(fallback_url, wait_until="domcontentloaded")
    await asyncio.sleep(2.0)
    await page.bring_to_front()
    return page


def extract_code_or_text(raw_text: str, code_elements_text: list[str], wrap_for_roblox_luau: bool = True) -> str:
    """Extracts the cleanest Luau code block or falls back to raw response."""
    if not wrap_for_roblox_luau:
        return raw_text.strip()
    if code_elements_text:
        # Return the latest code block
        latest_code = code_elements_text[-1].strip()
        if latest_code:
            return latest_code

    # Fallback to markdown regex extraction
    matches = re.findall(r"```(?:luau|lua)?\s*([\s\S]*?)```", raw_text, re.IGNORECASE)
    if matches:
        return matches[-1].strip()

    return raw_text.strip()


async def ask_gemini(page: Page, full_prompt: str, timeout_seconds: int = 300, wrap_for_roblox_luau: bool = True) -> str:
    """Sends prompt to Gemini Web and waits for response completion."""
    input_selectors = [
        "rich-textarea div[contenteditable='true']",
        "div.ql-editor",
        "div[contenteditable='true'][role='textbox']",
        "div[contenteditable='true']",
        "textarea"
    ]

    input_el = None
    for sel in input_selectors:
        try:
            el = await page.wait_for_selector(sel, state="visible", timeout=4000)
            if el:
                input_el = el
                break
        except Exception:
            continue

    if not input_el:
        raise RuntimeError(
            "Could not find Gemini input box. Ensure you are logged into https://gemini.google.com/app "
            "in the AIBridgeProfile Chrome browser."
        )

    # Focus and insert prompt using keyboard.insert_text (clipboard style, avoids premature enter)
    await input_el.click()
    await asyncio.sleep(0.3)
    await page.keyboard.insert_text(full_prompt)
    await asyncio.sleep(0.5)

    # Count existing assistant messages prior to sending
    prev_responses = await page.query_selector_all("message-content, .model-response-text")
    prev_count = len(prev_responses)

    # Click send button or press Enter
    send_selectors = [
        "button.send-button",
        "button[aria-label*='Send']",
        "button[aria-label*='Submit']",
        "send-button button",
        "div.send-button-container button"
    ]
    submitted = False
    for s_sel in send_selectors:
        btn = await page.query_selector(s_sel)
        if btn:
            is_disabled = await btn.get_attribute("disabled") or await btn.get_attribute("aria-disabled") == "true"
            if not is_disabled:
                try:
                    await btn.click()
                    submitted = True
                    break
                except Exception:
                    pass

    if not submitted:
        await page.keyboard.press("Enter")

    # Wait for completion: monitor text stabilization (2.5s) and absence of stop button
    stable_checks = 0
    last_text_len = -1
    max_wait_seconds = timeout_seconds
    elapsed = 0.0

    while stable_checks < 5 and elapsed < max_wait_seconds:
        await asyncio.sleep(0.5)
        elapsed += 0.5

        # Check for stop button indicator
        stop_btn = await page.query_selector(
            "button[aria-label*='Stop response'], button[aria-label*='Stop'], button.stop-button"
        )
        is_generating = (stop_btn is not None)

        responses = await page.query_selector_all("message-content, .model-response-text")
        if not responses:
            continue

        latest_resp = responses[-1]
        try:
            current_text = await latest_resp.inner_text()
        except Exception:
            current_text = ""

        curr_len = len(current_text.strip())

        # If a new response has arrived or lengthened, verify stability
        if curr_len > 0 and curr_len == last_text_len and not is_generating:
            stable_checks += 1
        else:
            stable_checks = 0
            last_text_len = curr_len

    if elapsed >= max_wait_seconds:
        raise TimeoutError(f"Gemini response timed out after {max_wait_seconds} seconds.")

    # Extract code blocks
    responses = await page.query_selector_all("message-content, .model-response-text")
    latest_resp = responses[-1]
    code_nodes = await latest_resp.query_selector_all("pre code, pre")
    code_texts = []
    for c in code_nodes:
        # Prefer child code element if available
        child = await c.query_selector("code")
        t = await (child or c).inner_text()
        if t.strip():
            code_texts.append(t.strip())

    full_resp_text = await latest_resp.inner_text()
    return extract_code_or_text(full_resp_text, code_texts, wrap_for_roblox_luau=wrap_for_roblox_luau)


async def ask_chatgpt(page: Page, full_prompt: str, timeout_seconds: int = 300, wrap_for_roblox_luau: bool = True) -> str:
    """Sends prompt to ChatGPT Web and waits for response completion."""
    input_selectors = [
        "#prompt-textarea",
        "div[contenteditable='true']#prompt-textarea",
        "textarea[name='prompt-textarea']",
        "textarea[id='prompt-textarea']",
        "textarea",
        "div[contenteditable='true']",
        "div[contenteditable]"
    ]

    input_el = None
    for sel in input_selectors:
        try:
            el = await page.wait_for_selector(sel, state="visible", timeout=4000)
            if el:
                input_el = el
                break
        except Exception:
            continue

    if not input_el:
        raise RuntimeError(
            "Could not find ChatGPT input box. Ensure you are logged into https://chatgpt.com "
            "in the AIBridgeProfile Chrome browser."
        )

    # Focus and insert prompt using keyboard.insert_text (clipboard style)
    await input_el.click()
    await asyncio.sleep(0.3)
    await page.keyboard.insert_text(full_prompt)
    await asyncio.sleep(0.5)

    # Click send button or press Enter
    send_selectors = [
        "button[data-testid='send-button']",
        "button[aria-label*='Send prompt']",
        "button[aria-label*='Send message']"
    ]
    submitted = False
    for s_sel in send_selectors:
        btn = await page.query_selector(s_sel)
        if btn:
            is_disabled = await btn.get_attribute("disabled") or await btn.get_attribute("aria-disabled") == "true"
            if not is_disabled:
                try:
                    await btn.click()
                    submitted = True
                    break
                except Exception:
                    pass

    if not submitted:
        await page.keyboard.press("Enter")

    # Wait for completion: button[data-testid='stop-button'] disappears AND text length remains unchanged for 2.5s (5 checks at 0.5s intervals)
    stable_checks = 0
    last_text_len = -1
    max_wait_seconds = timeout_seconds
    elapsed = 0.0

    while stable_checks < 5 and elapsed < max_wait_seconds:
        await asyncio.sleep(0.5)
        elapsed += 0.5

        stop_btn = await page.query_selector(
            "button[data-testid='stop-button'], button[aria-label*='Stop streaming'], button[aria-label*='Stop generating']"
        )
        is_generating = (stop_btn is not None)

        # Support both modern and legacy ChatGPT DOMs
        assistants = await page.query_selector_all(
            "div[data-markdown-text-style='assistant-message'], div[data-content-search-unit-key*='assistant'], div.MarkdownRoot-rZKhxa, div[data-message-author-role='assistant'], article, ol > li:has(pre), pre"
        )
        if not assistants:
            continue

        latest_resp = assistants[-1]
        try:
            current_text = await latest_resp.inner_text()
        except Exception:
            current_text = ""

        curr_len = len(current_text.strip())

        if curr_len > 0 and curr_len == last_text_len and not is_generating:
            stable_checks += 1
        else:
            stable_checks = 0
            last_text_len = curr_len

    if elapsed >= max_wait_seconds:
        raise TimeoutError(f"ChatGPT response timed out after {max_wait_seconds} seconds.")

    # Extract code blocks
    code_nodes = await page.query_selector_all("pre code, pre")
    code_texts = []
    for c in code_nodes:
        child = await c.query_selector("code")
        t = await (child or c).inner_text()
        if t.strip():
            code_texts.append(t.strip())

    assistants = await page.query_selector_all(
        "div[data-markdown-text-style='assistant-message'], div[data-content-search-unit-key*='assistant'], div.MarkdownRoot-rZKhxa, div[data-message-author-role='assistant'], article, ol > li:has(pre)"
    )
    latest_resp = assistants[-1] if assistants else None
    full_resp_text = await latest_resp.inner_text() if latest_resp else (code_texts[-1] if code_texts else "")
    return extract_code_or_text(full_resp_text, code_texts, wrap_for_roblox_luau=wrap_for_roblox_luau)


@mcp.tool()
async def ask_web_ai(
    provider: str,
    prompt: str,
    studio_context: str = "",
    wrap_for_roblox_luau: bool = True,
    timeout_seconds: int = 300
) -> str:
    """
    Sends a prompt and live Roblox Studio context to Gemini Web or ChatGPT Web via Chrome CDP.
    Returns the generated executable Luau VFX / 3D model script.

    Args:
        provider: 'gemini' or 'chatgpt'
        prompt: Task or modification instruction for the AI
        studio_context: Live Studio inspection data (selection, hierarchy, CFrames, attachments)
        wrap_for_roblox_luau: If True, wraps prompt with strict self-contained executable Luau output requirements
        timeout_seconds: Maximum seconds to wait for AI response completion (default: 300s / 5 minutes)
    """
    prov = provider.strip().lower()
    if prov not in ("gemini", "chatgpt"):
        return f"Error: Invalid provider '{provider}'. Choose either 'gemini' or 'chatgpt'."

    # Construct full prompt
    parts = []
    if studio_context and studio_context.strip():
        parts.append(f"[ROBLOX STUDIO LIVE CONTEXT]\n{studio_context.strip()}")

    parts.append(f"[TASK]\n{prompt.strip()}")

    if wrap_for_roblox_luau:
        parts.append(
            "[STRICT OUTPUT REQUIREMENTS]\n"
            "IMPORTANT: Output ONLY a single, self-contained, executable Roblox Studio ```luau code block "
            "that builds this VFX/3D model in Workspace and prints the created instance path. No markdown explanations outside the code block."
        )

    full_prompt = "\n\n".join(parts)

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            return (
                f"Error connecting to Chrome CDP on {CDP_URL}: {e}.\n"
                "Please run `launch_ai_browser.bat` first to start Chrome with remote debugging on port 9222."
            )

        try:
            page = await get_or_create_page(browser, prov)
            if prov == "gemini":
                return await ask_gemini(page, full_prompt, timeout_seconds=timeout_seconds, wrap_for_roblox_luau=wrap_for_roblox_luau)
            else:
                return await ask_chatgpt(page, full_prompt, timeout_seconds=timeout_seconds, wrap_for_roblox_luau=wrap_for_roblox_luau)
        except Exception as e:
            return f"Error executing ask_web_ai({prov}): {e}"


@mcp.tool()
async def collab_gemini_and_chatgpt(
    task_description: str,
    studio_context: str = "",
    architect: str = "gemini",
    reviewer: str = "chatgpt",
    timeout_seconds: int = 300
) -> str:
    """
    Two-stage AI collaboration:
    1. Architect (e.g. Gemini) generates v1 Roblox Luau VFX/Model script using live Studio context.
    2. Reviewer (e.g. ChatGPT) receives both Studio context and v1 script to optimize particle curves,
       TweenService easing, welds, attachments, and lighting, outputting the final executable Luau script.

    Args:
        task_description: Description of the VFX / 3D model to build
        studio_context: Live Roblox Studio context (selected instances, attachments, CFrames)
        architect: First AI provider ('gemini' or 'chatgpt')
        reviewer: Second AI provider ('chatgpt' or 'gemini')
        timeout_seconds: Maximum seconds to wait per AI stage (default: 300s / 5 minutes)
    """
    # Step 1: Architect generates initial script
    v1_script = await ask_web_ai(
        provider=architect,
        prompt=task_description,
        studio_context=studio_context,
        wrap_for_roblox_luau=True,
        timeout_seconds=timeout_seconds
    )

    if v1_script.startswith("Error"):
        return f"Architect ({architect}) step failed: {v1_script}"

    # Step 2: Reviewer enhances and polishes
    review_prompt = (
        "Review, enhance, and optimize this Roblox Luau VFX/Model script. "
        "Verify all Instance paths, CFrames, and Attachments against [ROBLOX STUDIO LIVE CONTEXT]. "
        "Upgrade the particle curves (NumberSequence, ColorSequence), TweenService easing, welds, and lighting. "
        "Return the final complete executable ```luau script.\n\n"
        f"[INITIAL V1 SCRIPT FROM {architect.upper()}]:\n```luau\n{v1_script}\n```"
    )

    final_script = await ask_web_ai(
        provider=reviewer,
        prompt=review_prompt,
        studio_context=studio_context,
        wrap_for_roblox_luau=True,
        timeout_seconds=timeout_seconds
    )

    return final_script


@mcp.tool()
async def list_open_ai_tabs() -> str:
    """
    Inspects Chrome on port 9222 and returns the status of open Gemini and ChatGPT tabs.
    """
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            return (
                f"Error connecting to Chrome CDP on {CDP_URL}: {e}.\n"
                "Please run `launch_ai_browser.bat` to start Chrome on port 9222."
            )

        lines = ["=== Open AI Browser Tabs (CDP 127.0.0.1:9222) ==="]
        found_any = False
        gemini_count = 0
        chatgpt_count = 0

        for ci, context in enumerate(browser.contexts):
            for pi, page in enumerate(context.pages):
                url = page.url
                title = await page.title()
                is_gemini = "gemini.google.com" in url.lower()
                is_chatgpt = "chatgpt.com" in url.lower()

                tag = ""
                if is_gemini:
                    tag = " [GEMINI TAB]"
                    gemini_count += 1
                elif is_chatgpt:
                    tag = " [CHATGPT TAB]"
                    chatgpt_count += 1

                lines.append(f"- Context {ci}, Page {pi}: '{title}' ({url}){tag}")
                found_any = True

        lines.append(f"\nSummary: {gemini_count} Gemini tab(s), {chatgpt_count} ChatGPT tab(s) detected.")
        if not found_any:
            lines.append("No open tabs found in the browser session.")

        return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
