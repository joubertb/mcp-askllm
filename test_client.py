import json
import subprocess
import sys

def main():
    """
    A simple test client for the MCP server.

    This client calls the server with the request as a command-line argument.
    """
    if len(sys.argv) != 3:
        print("Usage: python test_client.py <llm_name> \"<prompt>\"")
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

    try:
        # Run the server with the request as a command-line argument
        print(f"Sending request: {request_str}")
        result = subprocess.run(
            [sys.executable, "server.py", request_str],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"Received response: {result.stdout.strip()}")
        if result.stderr:
            print(f"Server errors:\n{result.stderr}")

    except subprocess.CalledProcessError as e:
        print(f"Error running server: {e}")
        print(f"Stderr: {e.stderr}")
    except FileNotFoundError:
        print("Error: 'server.py' not found. Make sure you are in the correct directory.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()