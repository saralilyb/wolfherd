# Controlling the kernel's network egress

wolfherd does not change *what* the Wolfram kernel talks to — it only changes
*how many* kernels exist. Before, each agent spawned its own `WolframKernel`;
after, there is exactly **one**, spawned by launchd
(`launchd` → `wolfherd-serve` → `wolfram` → `WolframKernel`). That makes the
egress surface a single process to reason about instead of one per agent.

## What egresses, and as whom

`mcp-proxy` itself only speaks loopback to the agents; it never reaches the
network. The process that egresses is the kernel binary, for cloud-backed
calls only:

- `WolframAlpha`, `Entity`, `FreeformPrompt`, `Quantity`, semantic search —
  these reach Wolfram's servers, authenticated as the licensed user.
- Pure local Wolfram Language (symbolic/numeric math, local file ops) does not
  touch the network.

So the real control is **local vs. cloud, per query** — not authentication.
There is no anonymous mode for cloud calls made under a named license.

## Pinning it down (macOS, e.g. Little Snitch)

Scope any per-process rule to the kernel, not the proxy:

- `/Applications/Wolfram.app/Contents/MacOS/WolframKernel`
- and its launcher `/Applications/Wolfram.app/Contents/MacOS/wolfram`

After wolfherd the parent process is `launchd`, not your terminal — update any
rule that keys on the parent.

Typical hosts a licensed kernel needs:

- `wolframcloud.com` (https) — cloud knowledge
- `wolframalpha.com` (https) — the `WolframAlpha` tool

Often droppable (test by denying):

- `wolframcdn.com` (https) — paclet/data downloads
- `wolfram.com` (http) — plaintext license/paclet ping

If you want a kernel that never egresses, deny the cloud hosts and keep usage to
local Wolfram Language; cloud-backed tools will fail closed rather than leak.
