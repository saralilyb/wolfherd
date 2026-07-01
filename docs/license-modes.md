# License modes

wolfherd's service shape is separable from the Wolfram license that backs it.
The config names the licensing assumption so operators do not accidentally treat
one mode as another.

## existing_desktop_single_kernel

This is the implemented default.

```sh
WOLFHERD_LICENSE_MODE=existing_desktop_single_kernel
```

wolfherd starts the same Wolfram command-line product an agent would have
started directly, but starts it once and shares it over HTTP MCP. This reduces
license pressure by keeping agent traffic behind one controlling process.

Operational rules:

- Keep `kernel_pool=1`.
- Keep parallel subkernels off unless your license has subprocess capacity.
- Run as the user whose Wolfram product is activated.
- Use `bin/wolfherd doctor --wolfram-smoke` before installing.

This mode does not create extra entitlement. If the GUI is open and wolfherd is
open, they may still consume separate controlling-process seats.

## free_engine_development

This is documented for future work, not implemented in this pass.

The intended appliance would use Wolfram Engine Community Edition with a
persistent activation volume. It is appropriate only where the Free Engine terms
permit the work: development, testing, demos, personal projects, or approved
open-source use.

Do not use this mode for paid/client/organizational production output unless
Wolfram confirms that your actual license permits it.

## production_engine

This is documented for future work, not implemented in this pass.

The same wolfherd surface could be backed by a production Wolfram Engine,
MathLM, site, cluster, or cloud/VM entitlement. That is the right mode for a
real service or organizational automation.

In this mode, wolfherd can eventually grow from one kernel to a licensed pool,
but the pool size must follow the purchased controlling-process and subprocess
limits.

## State models

`WOLFHERD_STATE_MODEL=global` is the current implementation. All clients share
`Global`` because the official Wolfram MCP server is proxied as one stateful
backend. `bin/wolfherd reset` clears that shared state.

`WOLFHERD_STATE_MODEL=namespace` is planned. It will require a broker layer that
wraps evaluator calls in leased Wolfram contexts and can clean up one client
namespace without clearing everyone else.
