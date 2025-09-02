# MCP-Ask-LLM Server

This project implements a **Model Context Protocol (MCP) server** that enables communication between different LLMs.  
For example, you can use this server to allow a Claude model to query a Gemini model and return the result.

Example interaction:

```text
claude: Ask Gemini to review the server.py file
claude: I'll use the Gemini agent to review the server.py file for you.
claude: gemini(Review server.py file)
...
claude: Gemini's review highlights several important areas for improvement in your MCP server. Here are the key findings:
claude: Critical Issues to Address
...
```

---

## Getting Started

### Integrating with Claude Code

#### Setup MCP
Add the MCP server to Claude:

```bash
claude mcp add mcp-askllm \
    -e ASKLLM_CONFIG=gemini \
    -e ASKLLM_GEMINI_MODEL=gemini/pro \
    -e ASKLLM_GEMINI_APIKEY=<apikey> \
    -- uvx --from git+https://github.com/joubertb/mcp-askllm mcp-askllm
```

#### Setup Agent
Use the example agents located in the `claude/agent` directory.  

This allows you to perform queries such as:

```text
Ask Gemini to review the plan you just proposed.
```

---

### Integrating with Gemini CLI

Add the following to your `~/.gemini/config.yaml` file:

```yaml
mcpServers:
  mcp-askllm:
    command: uvx
    args:
      - --from
      - git+https://github.com/joubertb/mcp-askllm
      - mcp-askllm
    env:
      ASKLLM_CONFIG: claude
      ASKLLM_CLAUDE_MODEL: claude/flash
      ASKLLM_CLAUDE_APIKEY: "<apikey>"
```

---

### Configure LLM Providers with Environment Variables

`mcp-askllm` is configured entirely via environment variables.  

1. Set `ASKLLM_CONFIG` to a comma-separated list of LLMs you want to enable.  
2. For each LLM, define its model and API key.  

Example (Gemini + Claude):

```bash
export ASKLLM_CONFIG="gemini,claude"
export ASKLLM_GEMINI_MODEL="gemini/gemini-pro"
export ASKLLM_GEMINI_APIKEY="YOUR_GEMINI_API_KEY"
export ASKLLM_CLAUDE_MODEL="claude-3-opus-20240229"
export ASKLLM_CLAUDE_APIKEY="YOUR_CLAUDE_API_KEY"

# Optional: Custom reference name for prompts
export ASKLLM_GEMINI_NAME="my_gemini"
```

#### Explanation of Environment Variables
- **`ASKLLM_CONFIG`**  
  A comma-separated list of LLM providers to enable (e.g., `gemini,claude`).  
- **`ASKLLM_<LLM_NAME_UPPER>_MODEL`**  
  The model identifier for the LLM (e.g., `ASKLLM_GEMINI_MODEL`).  
- **`ASKLLM_<LLM_NAME_UPPER>_APIKEY`**  
  The API key for the LLM (e.g., `ASKLLM_GEMINI_APIKEY`).  
- **`ASKLLM_<LLM_NAME_UPPER>_NAME`** *(optional)*  
  Custom alias for referencing the LLM in prompts. Defaults to the lowercase name from `ASKLLM_CONFIG`.  
