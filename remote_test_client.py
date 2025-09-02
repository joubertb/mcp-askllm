
import json
import subprocess
import sys

def main():
    """
    A test client that executes the MCP server from a git repository using uvx.
    """
    if len(sys.argv) != 3:
        print("Usage: python remote_test_client.py <llm_name> \"<prompt>\"")
        sys.exit(1)

    llm_name = sys.argv[1]
    prompt = sys.argv[2]

    request = {
        "jsonrpc": "2.0",
        "method": "ask",
        "params": [llm_name, prompt],
        "id": 1,
    }
    request_str = json.dumps(request)

    command = [
        "uvx",
        "--from",
        "git+https://github.com/joubertb/mcp-askllm",
        "mcp-askllm",
        request_str,
    ]

    try:
        print(f"Running command: {' '.join(command)}")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"Received response: {result.stdout.strip()}")
        if result.stderr:
            print(f"Server errors:\n{result.stderr}")

    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        print(f"Stderr: {e.stderr}")
    except FileNotFoundError:
        print("Error: 'uvx' not found. Make sure it is installed and in your PATH.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
