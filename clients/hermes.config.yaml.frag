# Hermes — ~/.hermes/config.yaml, under the existing "mcp_servers:" map.
# REPLACE the current command/args/env wolfram block with this url form.
# Keep the key lowercase on Hermes unless you intentionally want a new tool
# prefix; Claude examples keep "Wolfram" for permission-rule compatibility.

mcp_servers:
  wolfram:
    url: http://127.0.0.1:8765/mcp
    enabled: true
