# Running the case studies with Codex

The `codex/` folders inside the main-text experiments hold runs made with the Codex CLI (0.163.0, `gpt-5.6-sol`)
using the same MCP servers and prompts as the Claude Code runs. Each run was a fresh session in an isolated
filesystem view, so the agent could see only that case study's folder and the tool installations.

1. Copy a case-study directory (without `experiments/`) to a scratch folder and add the prompt as `PROMPT.txt`.
   For VISION, also copy `CLAUDE.md` to `AGENTS.md`.
2. Generate an isolated Codex configuration from the case study's `.mcp.json`
   (model and provider settings, MCP tools pre-approved, workspace-write sandbox with network for MPI):
   ```bash
   export AZURE_OPENAI_BASE_URL=https://<resource>.openai.azure.com/openai/v1   # and AZURE_API_KEY
   python make_codex_home.py <scratch dir> <python bin dir> [extra PATH dirs]
   ```
3. Start Codex inside the isolated view:
   ```bash
   RO_PATHS="<conda env> <lmp binary> <node/codex install>" HIDE_ROOT=/home \
     ./isolated.sh <scratch dir> bash -c 'CODEX_HOME=$PWD/.codex-home PATH=<python bin>:$PATH codex --no-daemon'
   ```
4. Paste the prompt from `PROMPT.txt`.
