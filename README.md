1# MCP-Ask-LLM Server

This project implements a Model Context Protocol (MCP) server in Python that facilitates communication with other LLMs. For example, you can use this server to allow a Claude model to ask a Gemini model a question and get an answer back.

## Getting Started

This project uses `pyproject.toml` for dependency management and `uv` as the recommended tool for installing and managing dependencies.

1.  **Install `uv`:**

    If you don't have `uv` installed, you can install it using `pipx` (recommended) or `pip`:

    ```bash
    pipx install uv
    # or
    pip install uv
    ```

2.  **Install the dependencies:**

    Navigate to the project root and install the dependencies:

    ```bash
    uv pip install .
    ```

    To create a lock file for reproducible builds (recommended for deployment):

    ```bash
    uv pip compile
    ```

    Then, to install from the lock file:

    ```bash
    uv pip install -r requirements.txt # uv will generate a requirements.txt.
    ```

2. **Configure your LLM providers using environment variables:**

   The server is configured using environment variables. You need to set `ASKLLM_CONFIG` to a comma-separated list of the LLM names you want to configure. Then, for each LLM, you need to set its model and API key.

   Here's an example for configuring Gemini and Claude:

   ```bash
   export ASKLLM_CONFIG="gemini,claude"
   export ASKLLM_GEMINI_MODEL="gemini/gemini-pro"
   export ASKLLM_GEMINI_APIKEY="YOUR_GEMINI_API_KEY"
   export ASKLLM_CLAUDE_MODEL="claude-3-opus-20240229"
   export ASKLLM_CLAUDE_APIKEY="YOUR_CLAUDE_API_KEY"
   # Optional: You can also set a custom name for the LLM to reference in prompts
   export ASKLLM_GEMINI_NAME="my_gemini"
   ```

   **Explanation of environment variables:**
   *   `ASKLLM_CONFIG`: A comma-separated list of the LLM providers you want to enable (e.g., `gemini`, `claude`). The names here will be used to construct the specific configuration variables.
   *   `ASKLLM_<LLM_NAME_UPPER>_MODEL`: The model identifier for the specific LLM (e.g., `ASKLLM_GEMINI_MODEL`).
   *   `ASKLLM_<LLM_NAME_UPPER>_APIKEY`: The API key for the specific LLM (e.g., `ASKLLM_GEMINI_APIKEY`).
   *   `ASKLLM_<LLM_NAME_UPPER>_NAME` (Optional): A custom name you want to use to refer to this LLM in the `ask` tool's `llm` argument. If not provided, it defaults to the lowercase version of the LLM name from `ASKLLM_CONFIG` (e.g., `gemini` for `ASKLLM_GEMINI_MODEL`).

## Integrating with Claude Code
```bash
   claude mcp add mcp-askllm \
        -e ASKLLM_CONFIG=gemini \
        -e ASKLLM_GEMINI_MODEL=gemini/pro \
        -e ASKLLM_GEMINI_APIKEY=<apikey> \
        -- uvx --from git+https://github.com/joubertb/mcp-askllm mcp-askllm
```

## Integrating with Gemini CLI

Add the following to your `~/.gemini/config.yaml` file:

```yaml
  "mcpServers": {
    "mcp-askllm": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/joubertb/mcp-askllm",
        "mcp-askllm"
      ],
      "env": {
        "ASKLLM_CONFIG": "claude",
        "ASKLLM_CLAUDE_MODEL": "claude/flash",
        "ASKLLM_CLAUDE_APIKEY": "<apikey>"
      }
    }
  }
```