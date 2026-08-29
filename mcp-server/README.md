# LVL MCP server

Exposes the LVL compiler as [Model Context Protocol](https://modelcontextprotocol.io)
tools, so Claude (or any MCP client) can drive LVL directly: hand it a program
and ask it to `check`, `assert`, `explain`, `discover`, find `contradictions`,
evaluate `constraints`, `emit_json`, or `diff`/`equiv` two programs.

This is the project's thesis wired into the agent loop: the model does the
language work; LVL returns the deterministic, sourced answer.

## Install

```bash
pip install -e ../reference-impl      # the lvl package
pip install "mcp[cli]"                 # the MCP SDK
```

## Run

```bash
python lvl_mcp.py        # stdio transport
```

## Add to Claude Code

```bash
claude mcp add lvl -- python /absolute/path/to/mcp-server/lvl_mcp.py
```

## Add to Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "lvl": {
      "command": "python",
      "args": ["/absolute/path/to/mcp-server/lvl_mcp.py"]
    }
  }
}
```

## Tools

| Tool | What it does |
|---|---|
| `check` | parse + type-check + provenance audit |
| `assert_proposition` | does a proposition hold, to a standard of proof? (with trace) |
| `explain` | full derivation tree for a proposition |
| `discover` | which elements are still missing |
| `contradictions` | disputed propositions + exclusivity violations |
| `constraints` | objective money/date/number checks |
| `emit_json` | the program as canonical JSON |
| `diff` / `equiv` | compare two programs structurally and semantically |

Each tool takes program **text** (not a path), so it works over any transport.
