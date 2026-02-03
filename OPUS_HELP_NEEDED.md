# CRITICAL ISSUE - Agent Hanging Indefinitely

## Problem Statement

A browser automation agent (using Playwright + Claude API) is **freezing after ~19 actions** and hanging for 16+ minutes before timeout.

**Expected behavior**: Complete 30 web challenges in <5 minutes  
**Actual behavior**: Hangs indefinitely after 19 actions, runs for 1111 seconds (18.5 minutes)

## Last Console Output

```
22:01:02 [DEBUG] [ 137.4s]   Action: scroll | body | The challenge mentions 'Hidden DOM Challenge'
22:17:16 [WARNING] [1111.2s] ⏰ TIME LIMIT EXCEEDED

Total Time:        1111.17s (1111166ms)
Challenges:        0/1 completed
LLM Usage:
  Total Calls:     19
  Input Tokens:    29,942
  Output Tokens:   1,419
Per-Challenge Breakdown:
  ✗ Challenge 1: 0ms, 19 actions, 19 LLM calls
```

**The agent froze for 974 seconds after attempting a scroll action.**

## Architecture

```
agent/
├── browser.py   # Playwright wrapper (BrowserController class)
├── runner.py    # Main loop (ChallengeRunner class)
├── tasks.py     # LLM interaction + action execution
├── llm.py       # Anthropic API client
└── metrics.py   # Run statistics
```

## Key Code Paths

### Main Loop (runner.py lines 81-186)
```python
while current_challenge <= MAX_CHALLENGES:
    # Check timeout
    if self.time_remaining() <= 0:
        self.metrics.finish(aborted=True, reason="Time limit exceeded")
        break
    
    browser.wait_for_dom_stable(timeout=500)
    dismissed = browser.dismiss_popups()
    state = detect_challenge_state(browser)
    
    if state.success_detected:
        # Auto-click advance buttons
        for btn_text in advance_buttons:
            browser.click_text(btn_text, timeout=500)
            browser.wait_for_dom_stable(timeout=500)  # ← SUSPECT!
            break
    
    action = get_agent_action(browser, self.llm, state)
    success = execute_action(browser, action)
    browser.page.wait_for_timeout(300)
```

### Suspect Function #1: wait_for_dom_stable (browser.py lines 150-161)
```python
def wait_for_dom_stable(self, timeout: int = 3000, check_interval: int = 200):
    import time as t
    last_html = ""
    start = t.time()
    while (t.time() - start) * 1000 < timeout:
        current_html = self.page.content()  # ← Could this hang?
        if current_html == last_html:
            return True
        last_html = current_html
        self.page.wait_for_timeout(check_interval)
    return False
```

**Issue**: If `self.page.content()` blocks or throws uncaught exception, this could loop forever.

### Suspect Function #2: dismiss_popups (browser.py lines 198-249)
```python
def dismiss_popups(self) -> int:
    dismissed = 0
    max_attempts = 10
    attempt = 0
    
    while attempt < max_attempts:  # ← Could this be infinite?
        found_any = False
        for selector in close_selectors:
            elements = self.page.locator(selector).all()
            for el in elements:
                if el.is_visible():
                    el.click(timeout=1000, force=True)
                    dismissed += 1
                    found_any = True
                    self.page.wait_for_timeout(300)
                    break
            if found_any:
                break
        if not found_any:
            break
        attempt += 1
    return dismissed
```

**Issue**: If popups keep reappearing, could loop forever. Also `el.is_visible()` might block.

### Suspect Function #3: Scroll action (tasks.py lines 251-262)
```python
elif action.action == "scroll":
    if action.value:
        if str(action.value).lower() == "bottom":
            browser.scroll_to_bottom()
        else:
            pixels = int(action.value)
            browser.scroll_down(pixels)
    else:
        browser.scroll_down(500)
    return True
```

```python
# browser.py
def scroll_down(self, pixels: int = 500):
    self.page.evaluate(f"window.scrollBy(0, {pixels})")
    self.page.wait_for_timeout(300)  # ← Could this hang?
```

## Observations

1. **Timeout mechanism not working**
   - Configured: `timeout=300` (5 minutes)
   - Actual runtime: 1111s (18.5 minutes)
   - The `if self.time_remaining() <= 0` check never triggered

2. **Debug logs missing**
   - Added logging for "Detected challenge #X from page"
   - NONE appeared in output
   - Main loop likely stopped executing

3. **Metrics show 0ms duration**
   - Suggests challenge metrics never finished
   - Time tracking broke

4. **Last action was scroll**
   - "Hidden DOM Challenge" mentioned
   - Never recovered after scroll

## What We Need

### 1. Add Aggressive Timeouts
Wrap ALL Playwright operations in try-except with timeouts:
```python
try:
    self.page.content()  # Could hang
except Exception as e:
    # Log and continue
```

### 2. Add Heartbeat Logging
Every iteration of main loop should log something like:
```python
self.log(f"[HEARTBEAT] Loop iteration {i}, challenge {current_challenge}")
```

This will show us exactly where it hangs.

### 3. Fix Timeout Enforcement
The timeout check happens inside the loop, but if the loop stops running, it never checks. Need a signal-based timeout or thread-based watchdog.

### 4. Graceful Degradation
If `wait_for_dom_stable()` takes >5 seconds, just give up and continue:
```python
try:
    with timeout(5):
        browser.wait_for_dom_stable()
except TimeoutError:
    self.log("DOM stability wait timed out, continuing anyway")
```

## Questions for Opus

1. **Where is the most likely hang point?**
   - `wait_for_dom_stable()`?
   - `dismiss_popups()`?
   - Playwright's `page.content()` or `page.wait_for_timeout()`?

2. **Why didn't the 300s timeout trigger?**
   - The main loop checks `if self.time_remaining() <= 0`
   - But it ran for 1111s
   - Is the loop completely blocked?

3. **How to add fail-safes?**
   - Should we wrap every browser action in a timeout decorator?
   - Use asyncio timeouts?
   - Use threading.Timer?

4. **Best debugging approach?**
   - Add heartbeat logs every 1 second?
   - Add timestamps to every log line? (already have this)
   - Use Playwright's debug mode?

## Progress So Far

The agent logic is actually quite good:
- ✅ Popup dismissal works (when it runs)
- ✅ Auto-submit after typing works
- ✅ Success detection works
- ✅ Challenge regex fixed to detect "Step X of 30"
- ✅ Scroll actions added
- ❌ **Agent hangs after ~19 actions**

This is a **timeout/exception handling issue**, not a logic issue. We're 95% there, just need to make it robust against hangs.

## Files to Review

1. `/Users/ckdev/Downloads/adcock-challenge/agent/runner.py` - Main loop
2. `/Users/ckdev/Downloads/adcock-challenge/agent/browser.py` - Browser operations
3. `/Users/ckdev/Downloads/adcock-challenge/agent/tasks.py` - Action execution

All files are available in the workspace.
