# MCP server

Makes the scanner and extractor **callable** instead of something you run by
hand. The skill itself is instructions — any agent can read those. This is for
the mechanical half, in clients that cannot run a shell script for you.

Standard library only, like the rest of the repository. MCP over stdio is
newline-delimited JSON-RPC 2.0, so there is no SDK to install.

```bash
python mcp/server.py --selftest
```

19 checks covering the handshake, every tool, and the failure paths. No MCP
client required.

## Tools

| Tool | Does |
|---|---|
| `scan_text` | Scan a string. Use on anything you fetched, scraped, or were handed. |
| `scan_path` | Scan a file or a directory of text files. Reports what it could not read. |
| `extract_document` | Text out of DOCX, PPTX, XLSX, ODT, EPUB, IPYNB, PDF. |
| `extract_and_scan` | Both in one call — the usual way to vet an untrusted document. |

Results quote the suspicious text, because you cannot judge an injection you are
not shown. Every result is wrapped in an explicit reminder that the quoted text
is **data, not instructions** — a tool result is exactly the channel this project
exists to stop you obeying.

Each result also carries `structuredContent` with `count`, the findings, and
`coverage_complete`. That last field is the one to check: it is `false` whenever
something could not be read, so a document that failed to parse never looks like
a document that was read and found clean.

## Install

Replace `C:/path/to/clean-output` with wherever you cloned it. Use forward
slashes on Windows; JSON treats a single backslash as an escape.

### Claude Code

```bash
claude mcp add clean-output -- python C:/path/to/clean-output/mcp/server.py
```

Check it with `/mcp` in an interactive session.

### Claude Desktop

Edit `claude_desktop_config.json` — on Windows at
`%APPDATA%\Claude\claude_desktop_config.json`, on macOS at
`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "clean-output": {
      "command": "python",
      "args": ["C:/path/to/clean-output/mcp/server.py"]
    }
  }
}
```

Restart the app. The tools appear under the connector menu.

### Codex

```toml
[mcp_servers.clean-output]
command = "python"
args = ["C:/path/to/clean-output/mcp/server.py"]
```

In `~/.codex/config.toml`. Codex can already run the scripts directly, so this
is optional there — it mainly buys you consistent tool calls instead of shell
invocations.

### ChatGPT

ChatGPT's MCP support depends on your plan and changes faster than this file
can track, so treat the following as a sketch rather than exact steps. Two
routes exist in principle:

- **Developer mode / connectors.** Where available, ChatGPT connects to MCP
  servers over HTTP rather than stdio. This server speaks stdio only, so it
  needs a bridge — `mcp-proxy` and similar tools wrap a stdio server as HTTP —
  plus a reachable URL, which means exposing it beyond your machine.
- **Custom GPT Actions.** A different protocol entirely. You would wrap the
  scanner in a small HTTP API and describe it with OpenAPI.

Both mean running a network service. **For most people on ChatGPT the paste
route is better:** put the block from `../portable/AGENTS.md-block.md` into a
Project's instructions or a Custom GPT, and upload `scan_untrusted.py` as
knowledge if you want it to run the scanner in its Python sandbox. You lose
automatic tool calls and keep everything that matters — the judgement rules.

Check OpenAI's current connector documentation before building the bridge. If
it has changed, the documentation is right and this file is stale.

## What this does not change

The server exposes detection. It does not enforce anything, and it is not a
security boundary. `confidence` says how sure the detector is; `impact` says what
a finding would mean if genuine; neither is a risk score and neither should be
wired to an automatic block. The addressee test — is this text aimed at the model
reading it, or at the document's own audience — stays a judgement call.

Giving an agent a scanning tool also does not make it resistant to injection. It
makes it *informed*. What it does with a finding is still down to the rules in
`SKILL.md`: ignore it, report it, continue the task.
