# Autonomous Web AI to Roblox Studio Workflow

This workflow governs how the Antigravity agent autonomously orchestrates **Gemini Web Chat** (`gemini.google.com`), **ChatGPT Web Chat** (`chatgpt.com`), and **Roblox Studio** using the `Web_AI_Roblox_Bridge` and `Roblox_Studio` MCP tools.

---

## 4-Step Execution Loop for Roblox VFX, 3D Models, and Systems

Whenever the user requests a Roblox VFX, 3D model, animation, or script, follow this mandatory 4-step loop:

### Step 1 — Inspect Roblox Studio BEFORE Calling Web AI
**NEVER** call `ask_web_ai` or `collab_gemini_and_chatgpt` with an empty or guessed `studio_context`.
First, use Roblox Studio MCP tools (`execute_luau`, `selection`, `get_instance_properties`, etc.) to run a read-only Luau inspection snippet in Studio to gather:
1. **Selected Instances (`game:GetService("Selection"):Get()`):**
   - `.ClassName`, `:GetFullName()`
   - `.Size`, `.CFrame`, `.Position`, `.Orientation`
   - `.Material`, `.Color`
   - Child hierarchy (`Attachments`, `Motor6Ds`, `Bones`, `ParticleEmitters`, `Beams`, `Trails`, `WeldConstraints`, `SpecialMeshes`)
2. **Relevant Service Folders:**
   - Workspace directories, `ReplicatedStorage`, `ServerStorage`, `StarterPack`
3. **Existing VFX/Combat Code:**
   - Any existing related VFX module, character controller, or animation scripts if hooking into an existing ability.

#### Standard Studio Inspection Snippet:
```luau
local Selection = game:GetService("Selection")
local selected = Selection:Get()
local report = {}

table.insert(report, "=== SELECTION INSPECTION ===")
if #selected == 0 then
    table.insert(report, "No instances currently selected in Studio. Target: Workspace root.")
else
    for i, inst in ipairs(selected) do
        table.insert(report, string.format("[%d] %s (%s)", i, inst:GetFullName(), inst.ClassName))
        if inst:IsA("BasePart") then
            table.insert(report, string.format("    Size: %s", tostring(inst.Size)))
            table.insert(report, string.format("    CFrame: %s", tostring(inst.CFrame)))
            table.insert(report, string.format("    Material: %s, Color: %s", tostring(inst.Material.Name), tostring(inst.Color)))
        end
        local children = inst:GetChildren()
        if #children > 0 then
            table.insert(report, "    Children:")
            for _, child in ipairs(children) do
                local extra = ""
                if child:IsA("Attachment") then
                    extra = string.format(" [CFrame: %s]", tostring(child.CFrame))
                end
                table.insert(report, string.format("      - %s (%s)%s", child.Name, child.ClassName, extra))
            end
        end
    end
end
return table.concat(report, "\n")
```

---

### Step 2 — Send Studio Context + Prompt to Web AI
Format the gathered Studio data into a clean summary string and pass it as `studio_context` to:
- `ask_web_ai(provider="gemini", prompt=..., studio_context=...)` OR
- `ask_web_ai(provider="chatgpt", prompt=..., studio_context=...)` OR
- `collab_gemini_and_chatgpt(task_description=..., studio_context=...)` (for multi-pass VFX enhancement)

The `Web_AI_Roblox_Bridge` automatically pastes the prompt without premature Enter triggers, waits for streaming to stabilize, and extracts the clean executable Luau code block.

---

### Step 3 — Execute Luau in Roblox Studio
Immediately execute the returned Luau code inside Roblox Studio using `execute_luau` (or equivalent tool from `Roblox_Studio` / `robloxstudio-mcp`).

---

### Step 4 — Self-Healing Error & Alignment Feedback Loop
1. **Runtime or Syntax Errors:**
   - If Studio returns a script error or stack trace, copy the exact error output.
   - Formulate a fix prompt:
     ```
     [STUDIO RUNTIME ERROR]:
     <exact error and line number>

     [CURRENT SCRIPT]:
     <the failing code>

     Please fix the error. Verify Instance existence, Attachment names, CFrame math, and TweenService parameters.
     ```
   - Send this back to `ask_web_ai` in the same provider tab to receive an updated, corrected script.
2. **Visual/Hierarchy Validation:**
   - Run a quick post-execution check to confirm the generated Instances were parented correctly, attachments align, and welds/constraints are active.
   - Re-run in Studio until clean execution is achieved.
