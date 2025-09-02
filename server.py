
import os
import logging
import json
import sys
import re
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from dotenv import load_dotenv
from fastmcp import FastMCP
from litellm import completion

# Optional secure storage (install with: pip install keyring)
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    logging.warning("keyring package not available. Using environment variables for API keys.")

# --- Logging Configuration ---
# --- Constants ---
DEFAULT_LOG_FILE = '/tmp/askllm.log'
MAX_PROMPT_LENGTH = 100000
CONFIG_ENV_VAR = "ASKLLM_CONFIG"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=DEFAULT_LOG_FILE,
    filemode='w',
)

# --- Custom Exceptions ---
class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass

class LLMConfigurationError(LLMError):
    """Exception raised when LLM configuration is invalid."""
    pass

class LLMResponseError(LLMError):
    """Exception raised when LLM response is invalid."""
    pass

# --- Configuration Classes ---
@dataclass
class LLMConfig:
    """Configuration for an LLM."""
    model: str
    api_key: str
    name: str
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None

# --- Input Validation ---
def validate_llm_name(llm: str) -> bool:
    """Validate LLM name contains only safe characters."""
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', llm))

def sanitize_prompt(prompt: str) -> str:
    """Basic prompt sanitization to remove potentially harmful content."""
    # Remove null bytes and control characters except newlines/tabs
    sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', prompt)
    return sanitized.strip()

# --- Error Handling ---
def handle_llm_error(error: Exception) -> str:
    """Centralized error handling for LLM operations."""
    if isinstance(error, ConnectionError):
        return "Error: Unable to connect to LLM service"
    elif isinstance(error, TimeoutError):
        return "Error: LLM request timed out"
    elif isinstance(error, ValueError):
        return "Error: Invalid request parameters"
    elif isinstance(error, LLMResponseError):
        return f"Error: {str(error)}"
    elif isinstance(error, LLMConfigurationError):
        return f"Error: {str(error)}"
    else:
        logging.error(f"Unexpected error: {error}", exc_info=True)
        return "Error: Unexpected error occurred"

# --- Stdio Logging Wrappers ---
class StdinLogger:
    def __init__(self, original_stdin: Any) -> None:
        self.original_stdin = original_stdin

    def readline(self, *args: Any, **kwargs: Any) -> str:
        line = self.original_stdin.readline(*args, **kwargs)
        # Only log non-sensitive parts
        logging.debug(f"STDIN <<< [message received, length={len(line)})")
        return line

    def __getattr__(self, name: str) -> Any:
        return getattr(self.original_stdin, name)

class StdoutLogger:
    def __init__(self, original_stdout: Any) -> None:
        self.original_stdout = original_stdout

    def write(self, data: str) -> None:
        # Only log non-sensitive parts
        logging.debug(f"STDOUT >>> [message sent, length={len(data)}]")
        self.original_stdout.write(data)

    def flush(self, *args: Any, **kwargs: Any) -> None:
        self.original_stdout.flush(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.original_stdout, name)

# --- Main Application Setup ---
load_dotenv()
logging.info("Starting server and loading .env file")

mcp = FastMCP()

# --- Secure API Key Management ---
def get_secure_api_key(service_name: str, username: str) -> Optional[str]:
    """Get API key from secure storage, falling back to environment variables."""
    if KEYRING_AVAILABLE:
        try:
            api_key = keyring.get_password(service_name, username)
            if api_key:
                logging.debug(f"Retrieved API key from keyring for {service_name}")
                return api_key
        except Exception as e:
            logging.warning(f"Failed to retrieve API key from keyring: {e}")
    
    # Fallback to environment variable
    env_var = f"ASKLLM_{username.upper()}_APIKEY"
    api_key = os.environ.get(env_var)
    if api_key:
        logging.debug(f"Retrieved API key from environment variable {env_var}")
    return api_key

def store_secure_api_key(service_name: str, username: str, api_key: str) -> bool:
    """Store API key in secure storage."""
    if not KEYRING_AVAILABLE:
        logging.warning("keyring not available, cannot store API key securely")
        return False
    
    try:
        keyring.set_password(service_name, username, api_key)
        logging.info(f"Stored API key securely for {service_name}/{username}")
        return True
    except Exception as e:
        logging.error(f"Failed to store API key securely: {e}")
        return False

# --- LLM Configuration ---
def load_llm_configurations() -> Dict[str, LLMConfig]:
    """Load LLM configurations with secure API key management."""
    llm_configs: Dict[str, LLMConfig] = {}
    configured_llms_str = os.environ.get(CONFIG_ENV_VAR, "")
    
    if configured_llms_str:
        logging.info(f"Found ASKLLM_CONFIG with {len(configured_llms_str.split(','))} LLMs")
        for llm_name_upper in configured_llms_str.split(","):
            llm_name_upper = llm_name_upper.strip().upper()
            if not llm_name_upper:
                continue

            model_env_var = f"ASKLLM_{llm_name_upper}_MODEL"
            display_name_env_var = f"ASKLLM_{llm_name_upper}_NAME"

            model = os.environ.get(model_env_var)
            display_name = os.environ.get(display_name_env_var, llm_name_upper.lower())
            
            # Try to get API key from secure storage first
            api_key = get_secure_api_key("askllm", llm_name_upper.lower())

            if model and api_key:
                logging.info(f"Configuring LLM: {display_name}")
                llm_configs[display_name] = LLMConfig(
                    model=model,
                    api_key=api_key,
                    name=display_name
                )
            else:
                missing = []
                if not model:
                    missing.append("MODEL")
                if not api_key:
                    missing.append("APIKEY")
                logging.warning(f"Incomplete configuration for {llm_name_upper}. Missing: {', '.join(missing)}")
    else:
        logging.info("ASKLLM_CONFIG environment variable not set.")
    
    return llm_configs

llm_configs = load_llm_configurations()

# --- Rate Limiting ---
request_counts: Dict[str, List[float]] = {}
RATE_LIMIT_REQUESTS = 10  # requests per minute
RATE_LIMIT_WINDOW = 60.0  # seconds

def check_rate_limit(client_id: str = "default") -> bool:
    """Check if client has exceeded rate limit."""
    import time
    current_time = time.time()
    
    if client_id not in request_counts:
        request_counts[client_id] = []
    
    # Remove old requests outside the window
    request_counts[client_id] = [
        req_time for req_time in request_counts[client_id]
        if current_time - req_time < RATE_LIMIT_WINDOW
    ]
    
    # Check if under limit
    if len(request_counts[client_id]) >= RATE_LIMIT_REQUESTS:
        return False
    
    # Add current request
    request_counts[client_id].append(current_time)
    return True

# --- Tool Definition ---
# Note: FastMCP may not support async tools yet. For production async support,
# consider using aiohttp for HTTP requests within the synchronous function
# or migrate to a framework that supports async MCP tools.
@mcp.tool
def ask(llm: str, prompt: str) -> str:
    """Asks a question to another LLM."""
    try:
        # Rate limiting check
        if not check_rate_limit():
            logging.warning("Rate limit exceeded")
            return "Error: Rate limit exceeded. Please try again later."
        
        # Input validation
        if not llm or not isinstance(llm, str):
            raise ValueError("Invalid LLM parameter provided")
        
        if not validate_llm_name(llm):
            raise ValueError("LLM name contains invalid characters")
        
        if not prompt or not isinstance(prompt, str):
            raise ValueError("Invalid prompt parameter provided")
        
        if len(prompt) > MAX_PROMPT_LENGTH:
            raise ValueError(f"Prompt too long: {len(prompt)} characters (max: {MAX_PROMPT_LENGTH})")
        
        # Sanitize prompt
        sanitized_prompt = sanitize_prompt(prompt)
        if not sanitized_prompt:
            raise ValueError("Prompt is empty after sanitization")
        
        logging.info(f"'ask' tool called with llm='{llm}' and prompt length={len(sanitized_prompt)}")
        
        # Get LLM configuration
        llm_config = llm_configs.get(llm)
        if not llm_config:
            raise LLMConfigurationError(f"LLM '{llm}' not found in configuration. Check {CONFIG_ENV_VAR} and specific LLM environment variables.")

        logging.info(f"Sending completion request to model: {llm_config.model}")
        response = completion(
            model=llm_config.model,
            messages=[{"content": sanitized_prompt, "role": "user"}],
            api_key=llm_config.api_key,
        )
        
        # Safe response handling
        try:
            content = response.choices[0].message.content
            if not content:
                raise LLMResponseError("Empty response content")
            
            logging.info(f"Received response length: {len(content)}")
            return content
            
        except (IndexError, AttributeError) as e:
            logging.error(f"Invalid response structure: {e}")
            raise LLMResponseError("Invalid response structure from LLM")
        
    except (ValueError, LLMConfigurationError, LLMResponseError) as e:
        logging.error(f"Validation/Configuration error: {e}")
        return f"Error: {str(e)}"
    except Exception as e:
        logging.error(f"Unexpected error in ask function: {e}", exc_info=True)
        return handle_llm_error(e)

# --- Main Execution ---
def validate_test_request(request_str: str) -> tuple[str, str, Any]:
    """Validate and parse test mode request."""
    try:
        request = json.loads(request_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")
    
    if not isinstance(request, dict):
        raise ValueError("Request must be a JSON object")
    
    if "params" not in request:
        raise ValueError("Missing 'params' field in request")
    
    params = request["params"]
    if not isinstance(params, list) or len(params) < 2:
        raise ValueError("'params' must be a list with at least 2 elements")
    
    llm, prompt = params[0], params[1]
    
    if not isinstance(llm, str) or not isinstance(prompt, str):
        raise ValueError("LLM name and prompt must be strings")
    
    return llm, prompt, request.get("id", 1)

def main() -> None:
    """Main function to run the server or execute in test mode."""
    if len(sys.argv) > 1:
        # Test mode: process request from command line
        logging.info("Running in test mode")
        request_str = sys.argv[1]
        
        try:
            llm, prompt, request_id = validate_test_request(request_str)
            result = ask.fn(llm, prompt)
            response = {"jsonrpc": "2.0", "id": request_id, "result": result}
            print(json.dumps(response))
            logging.info("Test mode execution finished successfully.")
        except ValueError as e:
            error_response = {
                "jsonrpc": "2.0", 
                "id": None, 
                "error": {"code": -32602, "message": str(e)}
            }
            print(json.dumps(error_response))
            logging.error(f"Test mode validation error: {e}")
            sys.exit(1)
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0", 
                "id": None, 
                "error": {"code": -32603, "message": "Internal error"}
            }
            print(json.dumps(error_response))
            logging.error(f"Test mode execution error: {e}", exc_info=True)
            sys.exit(1)
    else:
        # Server mode: run the MCP server
        logging.info("Running in server mode")
        try:
            sys.stdin = StdinLogger(sys.stdin)
            sys.stdout = StdoutLogger(sys.stdout)
            mcp.run(transport="stdio")
        except Exception as e:
            logging.error(f"Server mode error: {e}", exc_info=True)
            sys.exit(1)

if __name__ == "__main__":
    main()
