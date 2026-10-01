# MCP server

Makes the scanner and extractor **callable** instead of something you run by
hand. The skill itself is instructions — any agent can read those. This is for
the mechanical half, in clients that cannot run a shell script for you.

Standard library only, like the rest of the repository. MCP over stdio is
newline-delimited JSON-RPC 2.0, so there is no SDK to install.

```bash
python mcp/server.py --selftest
```

30 checks covering the handshake, both transports, every tool, and the failure paths. No MCP
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

ChatGPT connects **inbound from OpenAI's servers** over HTTPS. It has no stdio
option, so a server on your laptop is unreachable no matter how it is
configured. The endpoint must be public and speak Streamable HTTP.

That is what `--http` mode is for, and `render.yaml` deploys it.

**One deliberate limitation.** HTTP mode serves `scan_text` only. The three
filesystem tools stay stdio-local, because a public endpoint that reads the
server's disk is a liability — `extract_document` pointed at an SSH key is a
read primitive for anyone who finds the URL, and a shared secret is not enough
to justify that. To check a document remotely, extract locally and send the
text.

#### Deploy

1. Push this repository to GitHub (already done if you cloned it from there).
2. Generate a secret:

   ```bash
   python -c "import secrets; print(secrets.token_hex(24))"
   ```

3. On [render.com](https://render.com): **New** → **Blueprint** → pick the repo.
   Render reads `render.yaml`. When prompted for `MCP_SHARED_SECRET`, paste the
   secret. Nothing is installed — the server has no dependencies.
4. Wait for the deploy, then confirm:

   ```bash
   curl https://<your-service>.onrender.com/health
   ```

   Expect `{"ok": true, ..., "tools": ["scan_text"]}`.

Free Render instances sleep when idle, so the first call after a quiet spell
takes a few seconds to wake.

#### Connect it

In ChatGPT: **Settings** → **Connectors** → **Advanced** → **Developer mode**,
then add a connector with

- **URL** `https://<your-service>.onrender.com/mcp`
- **Authentication** a bearer token, set to your secret

Developer mode and custom connectors are plan-dependent and the UI moves
around; if the labels differ, follow OpenAI's current connector documentation
rather than this file.

The same URL works anywhere that accepts a remote MCP server — Claude's custom
connectors, the Codex app, Codex in the browser. For Codex, add to
`~/.codex/config.toml`:

```toml
[mcp_servers.clean_output]
enabled = true
url = "https://<your-service>.onrender.com/mcp"

[mcp_servers.clean_output.http_headers]
Authorization = "Bearer <your-secret>"
```

#### Three ways to authenticate

Clients disagree about which headers you may set, so the server accepts any of:

| Method | For |
|---|---|
| `Authorization: Bearer <secret>` | ChatGPT and most clients |
| `X-MCP-Secret: <secret>` | Claude's connector UI, which reserves `Authorization` for OAuth |
| `?key=<secret>` | clients that let you set neither header |

Comparison is constant-time. Without `MCP_SHARED_SECRET` the endpoint is open,
and the server warns about it on every start.

#### Running it yourself

```bash
MCP_SHARED_SECRET=$(python -c "import secrets;print(secrets.token_hex(24))")   python mcp/server.py --http
```

Listens on `PORT`, default 8080. Any host works — Render is just one option, and
a tunnel such as Cloudflare Tunnel is fine for testing.

## What this does not change

The server exposes detection. It does not enforce anything, and it is not a
security boundary. `confidence` says how sure the detector is; `impact` says what
a finding would mean if genuine; neither is a risk score and neither should be
wired to an automatic block. The addressee test — is this text aimed at the model
reading it, or at the document's own audience — stays a judgement call.

Giving an agent a scanning tool also does not make it resistant to injection. It
makes it *informed*. What it does with a finding is still down to the rules in
`SKILL.md`: ignore it, report it, continue the task.
