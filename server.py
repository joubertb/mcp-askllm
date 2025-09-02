import asyncio
import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from litellm import completion

load_dotenv()

mcp = FastMCP()

llm_configs = {}
configured_llms_str = os.environ.get("ASKLLM_CONFIG", "")
if configured_llms_str:
    for llm_name_upper in configured_llms_str.split(","):
        llm_name_upper = llm_name_upper.strip().upper()
        if not llm_name_upper:
            continue

        model_env_var = f"ASKLLM_{llm_name_upper}_MODEL"
        api_key_env_var = f"ASKLLM_{llm_name_upper}_APIKEY"
        display_name_env_var = f"ASKLLM_{llm_name_upper}_NAME"

        model = os.environ.get(model_env_var)
        api_key = os.environ.get(api_key_env_var)
        display_name = os.environ.get(display_name_env_var, llm_name_upper.lower())

        if model and api_key:
            llm_configs[display_name] = {
                "model": model,
                "api_key": api_key,
                "name": display_name
            }
        else:
            print(f"Warning: Incomplete configuration for {llm_name_upper}. Missing MODEL or APIKEY environment variable.")


@mcp.tool
def ask(llm: str, prompt: str) -> str:
    """Asks a question to another LLM.

    This tool should be used when you need to get information from another LLM.
    For example, if you are a specialized LLM and the user asks a general question, you can use this tool to ask a more general-purpose LLM for an answer.

    To use this tool, provide the name of the LLM you want to talk to and the prompt you want to send.

    Args:
        llm: The name of the LLM to ask.
        prompt: The prompt to send to the LLM.

    Returns:
        The text response from the LLM.
    """
    llm_config = llm_configs.get(llm)
    if not llm_config:
        return f"Error: LLM '{llm}' not found in configuration. Check ASKLLM_CONFIG and specific LLM environment variables."

    try:
        response = completion(
            model=llm_config["model"],
            messages=[{"content": prompt, "role": "user"}],
            api_key=llm_config.get("api_key"),
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"


import json

def main():
    import sys
    if len(sys.argv) > 1:
        request_str = sys.argv[1]
        request = json.loads(request_str)
        llm = request["params"][0]
        prompt = request["params"][1]
        result = ask.fn(llm, prompt)
        response = {"jsonrpc": "2.0", "id": request["id"], "result": result}
        print(json.dumps(response))
    else:
        mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
