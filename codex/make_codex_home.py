"""Write an isolated CODEX_HOME/config.toml for one case-study scratch dir.

Translates the case study's .mcp.json (Claude Code format) into Codex
[mcp_servers.*] tables. Only host settings are added (model, provider,
sandbox, timeouts, environment); the MCP servers themselves are unchanged.

Usage: make_codex_home.py <scratch_dir> <python_bin_dir> [extra PATH entries...]
"""
import json
import os
import sys

scratch = os.path.realpath(sys.argv[1])
py_bin = sys.argv[2]
path = ":".join([py_bin, *sys.argv[3:], "/usr/local/bin", "/usr/bin", "/bin"])
home = os.path.join(scratch, ".codex-home")
os.makedirs(home, exist_ok=True)


def q(s):
    return json.dumps(s)  # TOML basic strings are JSON-compatible here


servers = json.load(open(os.path.join(scratch, ".mcp.json")))["mcpServers"]
lines = [
    'model = "gpt-5.6-sol"',
    'model_provider = "azure"',
    'model_reasoning_effort = "medium"',
    'approval_policy = "never"',
    'sandbox_mode = "workspace-write"',
    "",
    "[sandbox_workspace_write]",
    "network_access = true  # MPI (mpirun) needs sockets",
    "",
    "[model_providers.azure]",
    'name = "Azure OpenAI"',
    f'base_url = {q(os.environ["AZURE_OPENAI_BASE_URL"])}',
    'env_key = "AZURE_API_KEY"',
    'wire_api = "responses"',
    "",
    f"[projects.{q(scratch)}]",
    'trust_level = "trusted"',
]
for name, s in servers.items():
    cmd = s["command"]
    if cmd in ("python", "python3"):
        cmd = os.path.join(py_bin, "python")
    env = {"PATH": path, "HOME": os.environ["HOME"], "MPLBACKEND": "Agg"}
    for k, v in s.get("env", {}).items():
        env[k] = v
    if os.path.isdir(os.path.join(scratch, "atomagents-mcp")):
        env["PYTHONPATH"] = os.path.join(scratch, "atomagents-mcp", "src")
    lines += [
        "",
        f"[mcp_servers.{q(name)}]",
        f"command = {q(cmd)}",
        f"args = {json.dumps(s.get('args', []))}",
        f"cwd = {q(scratch)}",
        "startup_timeout_sec = 60",
        "tool_timeout_sec = 7200",
        'default_tools_approval_mode = "approve"',
        "env = { " + ", ".join(f"{k} = {q(v)}" for k, v in env.items()) + " }",
    ]
open(os.path.join(home, "config.toml"), "w").write("\n".join(lines) + "\n")
print(os.path.join(home, "config.toml"))
