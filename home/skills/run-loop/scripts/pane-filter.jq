# Renders `claude -p --output-format stream-json --verbose` events as plain lines for a view pane.
# Usage: tail -n +1 -f <log>.jsonl | jq -r --unbuffered -f pane-filter.jq
if .type == "system" and .subtype == "init" then
  "[start] model=\(.model) mode=\(.permissionMode)"
elif .type == "assistant" then
  (.message.content[]?
   | if .type == "text" then .text
     elif .type == "tool_use" then "[tool] \(.name) \(.input | tostring | .[0:160])"
     else empty end)
elif .type == "result" then
  "[done] \(.subtype) denied=\(.permission_denials | length)"
else empty end
