# JVL MCP server

Exposes the JVL compiler as [Model Context Protocol](https://modelcontextprotocol.io)
tools, so Claude (or any MCP client) can drive JVL directly: hand it a program
and ask it to `check`, `assert`, `explain`, `discover`, find `contradictions`,
evaluate `constraints`, `emit_json`, or `diff`/`equiv` two programs.

This is the project's thesis wired into the agent loop: the model does the
language work; JVL returns the deterministic, sourced answer.

## Install

```bash
pip install -e ../reference-impl      # the jvl package
pip install "mcp[cli]"                 # the MCP SDK
```

## Run

```bash
python jvl_mcp.py        # stdio transport
```

## Add to Claude Code

```bash
claude mcp add jvl -- python /absolute/path/to/mcp-server/jvl_mcp.py
```

## Add to Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "jvl": {
      "command": "python",
      "args": ["/absolute/path/to/mcp-server/jvl_mcp.py"]
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
