"""Browser automation agent for solving web challenges."""

from .browser import BrowserController
from .llm import get_client, LLMClient, AnthropicClient, OpenAIClient
from .tasks import detect_challenge_state, get_agent_action, execute_action
from .metrics import RunMetrics, ChallengeMetrics
from .runner import ChallengeRunner, run_challenge

__all__ = [
    "BrowserController",
    "get_client",
    "LLMClient", 
    "AnthropicClient",
    "OpenAIClient",
    "detect_challenge_state",
    "get_agent_action",
    "execute_action",
    "RunMetrics",
    "ChallengeMetrics",
    "ChallengeRunner",
    "run_challenge",
]
