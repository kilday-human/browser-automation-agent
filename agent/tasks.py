"""Task interpretation and agent decision logic."""

import re
import json
from dataclasses import dataclass
from typing import Optional

from .browser import BrowserController
from .llm import LLMClient


SYSTEM_PROMPT = """You are a browser automation agent solving interactive challenges.

You will receive:
1. The visible text on the page
2. A list of interactive elements (buttons, inputs, etc.)
3. The current challenge number (if detected)

Your job: Analyze the challenge and return the EXACT action to take.

Respond with a JSON object containing ONE action:
{
    "action": "click" | "type" | "select" | "press_key" | "scroll" | "wait" | "done",
    "selector": "CSS selector or text to target",
    "value": "text to type, pixels to scroll, or option to select",
    "reasoning": "brief explanation"
}

Action types:
- click: Click a button or link. Use selector like "button:has-text('Submit')" or "#button-id"
- type: Type into an input. Provide selector and value (Enter key will be pressed automatically)
- select: Select dropdown option. Provide selector and value
- press_key: Press keyboard key (e.g., "Enter", "Tab")
- scroll: Scroll down. Provide value in pixels (e.g., "500") or "bottom"
- wait: Wait for page update (use sparingly)
- done: Challenge appears complete, move to next

IMPORTANT PATTERNS:
- If text says "scroll to reveal", use scroll action with required pixels
- If you see revealed codes/secrets, remember them for the next challenge
- After clicking "Reveal Code" or similar, the next step is usually to enter that code
- Look for Advance/Next/Continue/Proceed buttons to move to next challenge
- If a challenge says "correct" or "success", look for Next/Advance button or use "done"
- CRITICAL: If challenge mentions "Hidden DOM", "HTML attributes", "data-challenge-code", or "inspect HTML":
  The code is IN THE PAGE HTML (not visible text). You CANNOT see it with normal actions.
  Just enter any 6-digit code (like "123456") to try submitting - the system will handle DOM inspection.

Be precise and concise. Output valid JSON only."""


USER_PROMPT_TEMPLATE = """Current page state:

VISIBLE TEXT:
{page_text}

INTERACTIVE ELEMENTS:
{elements}

CHALLENGE INFO:
{challenge_info}

What single action should I take next? Respond with JSON only."""


@dataclass
class AgentAction:
    action: str
    selector: Optional[str] = None
    value: Optional[str] = None
    reasoning: str = ""

    @classmethod
    def from_json(cls, data: dict) -> "AgentAction":
        return cls(
            action=data.get("action", "wait"),
            selector=data.get("selector"),
            value=data.get("value"),
            reasoning=data.get("reasoning", ""),
        )


@dataclass
class ChallengeState:
    number: Optional[int]
    title: Optional[str]
    description: str
    is_complete: bool
    success_detected: bool = False
    error_detected: bool = False
    progress_indicator: Optional[str] = None


def detect_challenge_state(browser: BrowserController) -> ChallengeState:
    """Detect current challenge number and state from page."""
    text = browser.get_text()
    html = browser.get_html()
    
    # Try to find challenge number - PRIORITIZE "Step X of 30" pattern first
    number = None
    
    # Method 1: "Step X of 30" pattern (most reliable for this challenge)
    step_match = re.search(r"step\s+(\d+)\s+of\s+30", text, re.IGNORECASE)
    if step_match:
        number = int(step_match.group(1))
    
    # Method 2: "X of 30" or "X/30" patterns (fallback)
    if not number:
        progress_match = re.search(r"^(\d+)\s*(?:of|/)\s*30", text, re.IGNORECASE | re.MULTILINE)
        if progress_match:
            number = int(progress_match.group(1))
    
    # Method 3: Traditional "Challenge #X" patterns (last resort)
    if not number:
        number_match = re.search(r"(?:challenge|task|level|question)\s*[#:]?\s*(\d+)", text, re.IGNORECASE)
        if number_match:
            number = int(number_match.group(1))
    
    # Detect success indicators (challenge completed correctly)
    success_indicators = ["correct", "success", "well done", "great job", "✓", "✔", "passed"]
    success_detected = any(ind in text.lower() for ind in success_indicators)
    
    # Detect error indicators (wrong answer)
    error_indicators = ["incorrect", "wrong", "try again", "error", "✗", "✘", "failed"]
    error_detected = any(ind in text.lower() for ind in error_indicators)
    
    # Check if on final completion screen
    complete_indicators = ["completed", "all challenges", "congratulations", "finished all", "30/30", "30 of 30"]
    is_complete = any(ind in text.lower() for ind in complete_indicators)
    
    # Extract progress indicator if present
    progress = None
    progress_match = re.search(r"(\d+\s*(?:of|/)\s*\d+)", text)
    if progress_match:
        progress = progress_match.group(1)
    
    # Extract title if present
    title = None
    title_match = re.search(r"<h[12][^>]*>([^<]+)</h[12]>", html, re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()
    
    return ChallengeState(
        number=number,
        title=title,
        description=text[:500],
        is_complete=is_complete,
        success_detected=success_detected,
        error_detected=error_detected,
        progress_indicator=progress,
    )


def format_elements(elements: list[dict]) -> str:
    """Format interactive elements for LLM consumption."""
    lines = []
    for i, el in enumerate(elements[:30]):  # Limit to 30 elements
        parts = [f"{i+1}. <{el['tag']}>"]
        if el["text"]:
            parts.append(f'text="{el["text"][:50]}"')
        if el["placeholder"]:
            parts.append(f'placeholder="{el["placeholder"]}"')
        if el["id"]:
            parts.append(f'id="{el["id"]}"')
        if el["type"]:
            parts.append(f'type="{el["type"]}"')
        if el["disabled"]:
            parts.append("(disabled)")
        parts.append(f'selector="{el["selector"]}"')
        lines.append(" ".join(parts))
    return "\n".join(lines) if lines else "No interactive elements found"


def get_agent_action(browser: BrowserController, llm: LLMClient, challenge_state: ChallengeState) -> AgentAction:
    """Ask LLM what action to take."""
    elements = browser.get_interactive_elements()
    page_text = browser.get_text()[:2000]
    
    challenge_info = f"Challenge #{challenge_state.number}" if challenge_state.number else "Unknown challenge"
    if challenge_state.title:
        challenge_info += f": {challenge_state.title}"
    
    user_prompt = USER_PROMPT_TEMPLATE.format(
        page_text=page_text,
        elements=format_elements(elements),
        challenge_info=challenge_info,
    )
    
    response = llm.call(SYSTEM_PROMPT, user_prompt)
    
    # Parse JSON from response
    try:
        # Handle markdown code blocks
        content = response.content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
        
        data = json.loads(content)
        return AgentAction.from_json(data)
    except (json.JSONDecodeError, KeyError) as e:
        # Fallback: try to extract action from text
        if "click" in response.content.lower():
            return AgentAction(action="click", selector="button", reasoning=f"Parse error, attempting click: {e}")
        return AgentAction(action="wait", reasoning=f"Failed to parse LLM response: {e}")


def execute_action(browser: BrowserController, action: AgentAction) -> bool:
    """Execute an action in the browser. Returns True if successful."""
    try:
        if action.action == "click":
            if action.selector:
                strategies = [
                    lambda: browser.click(action.selector, timeout=3000),
                ]
                # Add fallback strategies
                if "text" in action.selector.lower() or action.selector.startswith('"'):
                    text = re.search(r'"([^"]+)"', action.selector)
                    if text:
                        strategies.append(lambda t=text.group(1): browser.click_text(t))
                        strategies.append(lambda t=text.group(1): browser.page.get_by_role("button", name=t).click(timeout=3000))
                
                for strategy in strategies:
                    try:
                        strategy()
                        return True
                    except:
                        continue
                return False
            return True
            
        elif action.action == "type":
            if action.selector and action.value:
                strategies = [
                    lambda: browser.type_text(action.selector, action.value),
                    lambda: browser.page.locator(action.selector).fill(action.value),
                    lambda: browser.page.locator("input:visible, textarea:visible").first.fill(action.value),
                ]
                # Try placeholder-based if selector looks like placeholder text
                if not action.selector.startswith("#") and not action.selector.startswith("."):
                    strategies.insert(1, lambda: browser.type_into_placeholder(action.selector, action.value))
                
                for strategy in strategies:
                    try:
                        strategy()
                        # Auto-press Enter after typing (common pattern for form submission)
                        try:
                            browser.press_key("Enter")
                        except:
                            pass  # If Enter doesn't work, that's okay
                        return True
                    except:
                        continue
                return False
            return True
            
        elif action.action == "select":
            if action.selector and action.value:
                try:
                    browser.select_option(action.selector, action.value)
                except:
                    # Try by visible text
                    browser.page.locator(action.selector).select_option(label=action.value)
            return True
            
        elif action.action == "press_key":
            if action.value:
                browser.press_key(action.value)
            return True
        
        elif action.action == "scroll":
            if action.value:
                if str(action.value).lower() == "bottom":
                    browser.scroll_to_bottom()
                else:
                    try:
                        pixels = int(action.value)
                        browser.scroll_down(pixels)
                    except:
                        browser.scroll_down(500)  # Default scroll
            else:
                browser.scroll_down(500)
            return True
            
        elif action.action == "wait":
            browser.wait_for_dom_stable(timeout=1000)
            browser.wait_for_no_spinners(timeout=2000)
            return True
            
        elif action.action == "done":
            return True
            
        return False
        
    except Exception as e:
        print(f"  Action failed: {e}")
        return False


def get_action_with_vision(browser: BrowserController, llm, challenge_state: ChallengeState) -> AgentAction:
    """Fallback: use vision model when text-based approach fails."""
    screenshot = browser.take_screenshot_base64()
    
    vision_prompt = """Look at this screenshot of a browser challenge. 
The text-based approach has failed multiple times.

What action should I take? Look for:
- Buttons to click
- Input fields to fill
- Visual puzzles or patterns
- Any interactive elements

Respond with JSON: {"action": "click"|"type"|"select", "selector": "description", "value": "if needed", "reasoning": "what you see"}"""
    
    if hasattr(llm, 'call_with_image'):
        response = llm.call_with_image(SYSTEM_PROMPT, vision_prompt, screenshot)
        try:
            content = response.content.strip()
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\s*", "", content)
                content = re.sub(r"\s*```$", "", content)
            data = json.loads(content)
            return AgentAction.from_json(data)
        except:
            pass
    
    return AgentAction(action="wait", reasoning="Vision fallback failed")
