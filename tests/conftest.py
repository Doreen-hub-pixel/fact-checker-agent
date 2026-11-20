import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

# Update to Groq
if not os.environ.get("GROQ_API_KEY"):
    os.environ["GROQ_API_KEY"] = "gsk-dummy-key-for-testing"
if not os.environ.get("TAVILY_API_KEY"):
    os.environ["TAVILY_API_KEY"] = "tvly-dummy-key-for-testing"


def pytest_configure(config):
    """Ignore third-party deprecation warnings for a clean test output."""
    import warnings

    warnings.filterwarnings("ignore", category=DeprecationWarning)
    