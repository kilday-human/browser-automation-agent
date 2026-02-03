"""Main runner coordinating browser, LLM, and challenge progression."""

import time
import logging
from enum import Enum
from typing import Optional

from .browser import BrowserController
from .llm import LLMClient, get_client
from .tasks import detect_challenge_state, get_agent_action, execute_action, get_action_with_vision
from .metrics import RunMetrics

TARGET_URL = "https://serene-frangipane-7fd25b.netlify.app"
MAX_TIME_SECONDS = 300  # 5 minutes
MAX_CHALLENGES = 30
MAX_ACTIONS_PER_CHALLENGE = 8  # Reduced from 20 - force faster decisions!
MAX_CONSECUTIVE_FAILURES = 3  # Reduced from 5 - fail faster
VISION_FALLBACK_THRESHOLD = 3  # Use vision after this many text failures


class ChallengePhase(Enum):
    LOADING = "loading"
    SOLVING = "solving"
    VALIDATING = "validating"
    TRANSITIONING = "transitioning"
    COMPLETE = "complete"


class ChallengeRunner:
    def __init__(
        self,
        llm: LLMClient,
        headless: bool = True,
        timeout_seconds: int = MAX_TIME_SECONDS,
        verbose: bool = True,
        use_vision_fallback: bool = True,
    ):
        self.llm = llm
        self.headless = headless
        self.timeout = timeout_seconds
        self.verbose = verbose
        self.use_vision_fallback = use_vision_fallback
        self.metrics = RunMetrics()
        self.phase = ChallengePhase.LOADING
        
        # Setup logging
        logging.basicConfig(
            level=logging.DEBUG if verbose else logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)

    def log(self, msg: str, level: str = "info"):
        if self.verbose:
            elapsed = time.time() - self.metrics.start_time
            prefix = f"[{elapsed:6.1f}s]"
            getattr(self.logger, level)(f"{prefix} {msg}")

    def time_remaining(self) -> float:
        return self.timeout - (time.time() - self.metrics.start_time)

    def run(self) -> RunMetrics:
        """Run all challenges with timeout enforcement."""
        self.log(f"Starting challenge run (timeout: {self.timeout}s)")
        
        with BrowserController(headless=self.headless) as browser:
            try:
                self.log(f"Navigating to {TARGET_URL}")
                browser.goto(TARGET_URL)
                browser.wait_for_dom_stable()
                browser.wait_for_no_spinners()
                
                # Dismiss any initial popups before starting
                dismissed = browser.dismiss_popups()
                if dismissed > 0:
                    self.log(f"Dismissed {dismissed} initial popup(s)")
                    browser.page.wait_for_timeout(500)
                
                # Click START button to begin challenges
                self.log("Looking for START button...")
                try:
                    browser.click_text("START", timeout=5000)
                    self.log("✓ Clicked START button - challenges beginning!")
                    browser.wait_for_dom_stable()
                    browser.page.wait_for_timeout(1000)  # Wait for challenges to load
                except Exception as e:
                    self.log(f"No START button found (might already be in challenges): {e}", "debug")
                
                self.phase = ChallengePhase.SOLVING
                
                current_challenge = 1
                consecutive_failures = 0
                text_failures = 0  # Track for vision fallback
                last_challenge_number = None
                challenge_metrics = None
                challenge_start_time = {}  # Track time spent per challenge
                
                while current_challenge <= MAX_CHALLENGES:
                    # Check timeout
                    if self.time_remaining() <= 0:
                        self.metrics.finish(aborted=True, reason="Time limit exceeded")
                        self.log("⏰ TIME LIMIT EXCEEDED", "warning")
                        break
                    
                    # Wait for dynamic content
                    browser.wait_for_dom_stable(timeout=500)
                    
                    # AGGRESSIVE popup dismissal - run 3 times to catch all layers!
                    total_dismissed = 0
                    for _ in range(3):  # Try 3 rounds of dismissal
                        dismissed = browser.dismiss_popups()
                        total_dismissed += dismissed
                        if dismissed > 0:
                            browser.page.wait_for_timeout(300)  # Let animations complete
                    
                    if total_dismissed > 0:
                        self.log(f"  Dismissed {total_dismissed} popup(s) total", "debug")
                    
                    # Detect current state
                    state = detect_challenge_state(browser)
                    detected_num = state.number or current_challenge
                    
                    # Debug logging for challenge detection
                    if state.number:
                        self.log(f"  Detected challenge #{state.number} from page", "debug")
                    else:
                        self.log(f"  Challenge number not detected, using current: {current_challenge}", "debug")
                    
                    # Special handling for "Hidden DOM Challenge"
                    page_text = browser.get_text()
                    if "Hidden DOM Challenge" in page_text or "data-challenge-code" in page_text:
                        self.log("  Detected Hidden DOM Challenge - inspecting HTML attributes", "debug")
                        try:
                            codes = browser.find_data_attributes("data-challenge-code")
                            if codes:
                                code = list(codes.values())[0]
                                self.log(f"  Found hidden code: {code}", "debug")
                                # Try to enter the code
                                browser.type_text("input[placeholder*='code' i]", code)
                                browser.page.wait_for_timeout(500)
                                continue
                        except Exception as e:
                            self.log(f"  DOM inspection failed: {e}", "debug")
                    
                    # Log state changes
                    if state.success_detected:
                        self.log(f"  ✓ Success detected!", "info")
                        # Auto-try clicking advance buttons when success detected
                        advance_buttons = ["Advance", "Next Section", "Move On", "Keep Going", "Proceed", "Next", "Continue"]
                        for btn_text in advance_buttons:
                            try:
                                browser.click_text(btn_text, timeout=500)
                                self.log(f"  Auto-clicked '{btn_text}' after success", "debug")
                                browser.wait_for_dom_stable(timeout=500)
                                break
                            except:
                                continue
                    if state.error_detected:
                        self.log(f"  ✗ Error detected - may need retry", "warning")
                    
                    # Check if we've moved to a new challenge
                    if detected_num != last_challenge_number:
                        if last_challenge_number is not None and challenge_metrics:
                            self.metrics.complete_challenge(challenge_metrics, success=True)
                            self.log(f"✓ Challenge {last_challenge_number} completed!")
                        last_challenge_number = detected_num
                        current_challenge = detected_num
                        challenge_metrics = self.metrics.start_challenge(current_challenge)
                        challenge_start_time[current_challenge] = time.time()  # Track start time
                        self.log(f"Starting Challenge {current_challenge}" + 
                                (f" ({state.progress_indicator})" if state.progress_indicator else ""))
                        consecutive_failures = 0
                        text_failures = 0
                        self.phase = ChallengePhase.SOLVING
                    
                    # NUCLEAR OPTION: If stuck on Challenge 1 for >90s, force skip!
                    if current_challenge == 1 and current_challenge in challenge_start_time:
                        time_on_challenge = time.time() - challenge_start_time[current_challenge]
                        if time_on_challenge > 90:
                            self.log(f"⚠️  FORCE SKIPPING Challenge 1 after {time_on_challenge:.1f}s - popup hell!", "warning")
                            if challenge_metrics:
                                self.metrics.complete_challenge(challenge_metrics, success=False, error="Force skipped - popup hell")
                            # DON'T navigate - the challenge site doesn't have separate URLs per step
                            # Just mark as failed and let the loop continue
                            current_challenge = 2
                            last_challenge_number = 2
                            consecutive_failures = 0
                            text_failures = 0
                            browser.page.wait_for_timeout(1000)
                            continue
                    
                    # Check if all challenges complete
                    if state.is_complete and detected_num >= MAX_CHALLENGES:
                        if challenge_metrics:
                            self.metrics.complete_challenge(challenge_metrics, success=True)
                        self.log("🎉 ALL CHALLENGES COMPLETED!")
                        self.phase = ChallengePhase.COMPLETE
                        break
                    
                    # Get action - use vision fallback if text approach keeps failing
                    if text_failures >= VISION_FALLBACK_THRESHOLD and self.use_vision_fallback:
                        self.log("  Using vision fallback...", "debug")
                        action = get_action_with_vision(browser, self.llm, state)
                    else:
                        action = get_agent_action(browser, self.llm, state)
                    
                    if challenge_metrics:
                        challenge_metrics.llm_calls += 1
                    
                    self.log(f"  Action: {action.action} | {action.selector or action.value or ''} | {action.reasoning[:50] if action.reasoning else ''}", "debug")
                    
                    if action.action == "done":
                        self.phase = ChallengePhase.TRANSITIONING
                        # Try clicking advance buttons (more variations)
                        advance_buttons = [
                            "Advance", "Next Section", "Move On", "Keep Going", "Proceed",
                            "Next", "Continue", "Submit", "OK", "Go", "Forward"
                        ]
                        for btn_text in advance_buttons:
                            try:
                                browser.click_text(btn_text, timeout=1000)
                                self.log(f"  Clicked '{btn_text}' to advance", "debug")
                                break
                            except:
                                continue
                        browser.wait_for_dom_stable()
                        continue
                    
                    success = execute_action(browser, action)
                    if challenge_metrics:
                        challenge_metrics.actions_taken += 1
                    
                    if not success:
                        consecutive_failures += 1
                        text_failures += 1
                        self.log(f"  Action failed ({consecutive_failures} consecutive)", "warning")
                        
                        if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                            self.log(f"  Too many failures, moving on", "warning")
                            if challenge_metrics:
                                self.metrics.complete_challenge(
                                    challenge_metrics, 
                                    success=False, 
                                    error="Max consecutive failures"
                                )
                            # FORCE advance - click any Next/Advance button to unstick
                            self.log(f"  Attempting emergency skip to next challenge", "warning")
                            for btn in ["Next", "Advance", "Skip", "Continue", "Proceed"]:
                                try:
                                    browser.click_text(btn, timeout=1000)
                                    self.log(f"  Emergency clicked '{btn}'", "debug")
                                    break
                                except:
                                    continue
                            
                            current_challenge += 1
                            consecutive_failures = 0
                            text_failures = 0
                            browser.page.wait_for_timeout(1000)  # Wait for page transition
                            continue  # Skip to next loop iteration immediately
                    else:
                        consecutive_failures = 0
                        # Reset text failures on any success
                        if text_failures > 0:
                            text_failures = max(0, text_failures - 1)
                    
                    # Brief pause to let page update
                    browser.page.wait_for_timeout(300)
                    
                    # Safety check: don't loop forever on one challenge
                    if challenge_metrics and challenge_metrics.actions_taken >= MAX_ACTIONS_PER_CHALLENGE:
                        self.log(f"  Max actions reached for challenge {current_challenge}", "warning")
                        self.metrics.complete_challenge(
                            challenge_metrics,
                            success=False,
                            error="Max actions exceeded"
                        )
                        # FORCE advance - try to click Next/Advance to unstick
                        self.log(f"  Attempting emergency skip after max actions", "warning")
                        for btn in ["Next", "Advance", "Skip", "Continue", "Proceed"]:
                            try:
                                browser.click_text(btn, timeout=1000)
                                self.log(f"  Emergency clicked '{btn}'", "debug")
                                break
                            except:
                                continue
                        
                        current_challenge += 1
                        text_failures = 0
                        browser.page.wait_for_timeout(1000)  # Wait for page transition
                        continue  # Skip to next loop iteration immediately
                        
            except Exception as e:
                self.log(f"❌ Fatal error: {e}", "error")
                self.metrics.finish(aborted=True, reason=str(e))
                raise
            finally:
                if not self.metrics.end_time:
                    self.metrics.finish()
        
        return self.metrics


def run_challenge(
    provider: str = "anthropic",
    model: Optional[str] = None,
    headless: bool = True,
    timeout: int = MAX_TIME_SECONDS,
    output_file: str = "run_stats.json",
    verbose: bool = True,
    use_vision_fallback: bool = True,
) -> RunMetrics:
    """Convenience function to run the full challenge."""
    llm = get_client(provider, model)
    runner = ChallengeRunner(
        llm, 
        headless=headless, 
        timeout_seconds=timeout, 
        verbose=verbose,
        use_vision_fallback=use_vision_fallback,
    )
    
    metrics = runner.run()
    
    # Get LLM stats and save
    llm_stats = llm.stats.to_dict()
    metrics.save(output_file, llm_stats)
    metrics.print_summary(llm_stats)
    
    return metrics
