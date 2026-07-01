# Controlling the kernel's network egress

wolfherd does not change what the Wolfram kernel talks to. It changes how many
kernels exist. Before, each agent spawned its own `WolframKernel`; after, there
is exactly one supervised kernel. That makes the egress surface one process to
reason about instead of one process per agent.

## What egresses, and as whom

`mcp-proxy` speaks to local clients and the local stdio backend. The process
that egresses is the Wolfram kernel binary, for cloud-backed calls only:

- `WolframAlpha`, `Entity`, `FreeformPrompt`, `Quantity`, semantic search, and
  some data-resource downloads can reach Wolfram's servers, authenticated as
  the licensed user.
- Pure local Wolfram Language, symbolic/numeric computation, and local file
  operations do not need the network.

The real control is local vs. cloud, per query. There is no anonymous mode for
cloud calls made under a named license.

## Per-process firewall rules

Scope rules to the Wolfram kernel and launcher, not to `mcp-proxy`.

macOS examples:

```text
/Applications/Wolfram.app/Contents/MacOS/WolframKernel
/Applications/Wolfram.app/Contents/MacOS/wolfram
```

Windows examples:

```text
C:\Program Files\Wolfram Research\Wolfram\15.0\WolframKernel.exe
C:\Program Files\Wolfram Research\Wolfram\15.0\wolfram.exe
```

After wolfherd, the parent process is the supervisor (`launchd`, systemd, or a
Windows Scheduled Task), not the terminal or agent. Update any rule that keys on
parent process.

Typical Wolfram hosts for cloud-backed work:

```text
wolframcloud.com
wolframalpha.com
wolframcdn.com
wolfram.com
```

If you want a kernel that never egresses, deny the cloud hosts and keep usage to
local Wolfram Language; cloud-backed tools will fail closed rather than leak.
