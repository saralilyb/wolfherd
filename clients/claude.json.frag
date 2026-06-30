// Claude Code — ~/.claude.json, under the top-level "mcpServers" object.
// REPLACE the existing stdio "Wolfram" block with this. Keep the key named
// "Wolfram" so the rules in settings.json still match (ask on
// mcp__Wolfram__WolframLanguageEvaluator, deny on mcp__Wolfram__WolframContext).
//
// Claude Code 2.1.x speaks streamable-HTTP natively via type:"http".

"Wolfram": {
  "type": "http",
  "url": "http://127.0.0.1:8765/mcp"
}
