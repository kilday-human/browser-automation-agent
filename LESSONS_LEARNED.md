# Lessons Learned: Building an AI Browser Automation Agent

## Executive Summary

Built an autonomous agent to solve browser challenges using LLMs. The architecture is solid, the code works, but the project revealed a critical insight: **AI doesn't know what to ignore**.

For known, scripted environments, deterministic code beats AI agents by 10x on speed, cost, and reliability.

---

## What Worked: Architecture & Engineering

### 1. Multi-Provider Abstraction (`llm.py`)
```python
class LLMClient:
    def call(self, system: str, user: str) -> str:
        # Abstract interface
        
class AnthropicClient(LLMClient):
    # Anthropic implementation
    
class OpenAIClient(LLMClient):
    # OpenAI implementation
```

**Value:** Swap models instantly. Test Claude vs GPT-4 vs Haiku without changing agent logic.

**Production application:** Multi-cloud LLM deployments, A/B testing, cost optimization.

---

### 2. Observability First (`metrics.py`)
- Token tracking (input/output)
- Cost estimation per run
- Per-challenge timing
- Success/failure rates

**Value:** Know exactly what's expensive before deploying to production.

**Real-world parallel:** Managing autonomous vehicle test fleets—you instrument everything before scaling.

---

### 3. Graceful Degradation
- Text-based DOM parsing (fast, cheap)
- Vision fallback after 3 failures (slow, expensive, more reliable)
- Emergency skip after 8 actions (prevent infinite loops)

**Value:** System doesn't catastrophically fail when one approach doesn't work.

**Production application:** Healthcare AI, financial systems, anything safety-critical.

---

### 4. Modular Design
```
agent/
├── browser.py   # Playwright wrapper (swappable for Selenium, Puppeteer)
├── llm.py       # LLM abstraction (swappable providers)
├── tasks.py     # Action execution (testable independently)
├── metrics.py   # Observability (exportable to Datadog/CloudWatch)
└── runner.py    # Coordination (orchestrates everything)
```

**Value:** Test components independently. Replace parts without rewriting everything.

---

## What Didn't Work: When AI Costs Too Much

### The Automation Paradox

| Factor | AI Agent | Hardcoded Script |
|--------|----------|------------------|
| **Speed** | 5 minutes | 30 seconds |
| **Cost** | $0.15/run | $0/run |
| **Reliability** | 85-90% | 100% |
| **Setup Time** | 2 hours | 2 hours (manual solve + code) |
| **Adaptability** | Works on new challenges | Breaks on changes |

**For 30 known challenges:** Script wins.  
**For 1,000 unknown challenges:** AI wins.

---

### Why AI Struggled

**Problem 1: Fake Buttons**
- Challenge had "Close" buttons that don't actually close
- Real close button was a grey X in the corner
- Agent had to learn this through trial/error (expensive)
- Script just targets the correct element from Day 1

**Problem 2: Cookie Consent Blocking**
- Cookie banner blocked all interactions
- Agent tried clicking challenge buttons first (failed)
- Eventually learned to dismiss cookie consent first
- Script dismisses it on line 1

**Problem 3: Unnecessary Actions**
- Agent scrolled, clicked, typed, retried
- 20+ actions per challenge on average
- Script: 2-3 actions per challenge (only necessary ones)

**The core issue:** AI had to reason about what's *relevant*. Scripts ignore everything irrelevant by design.

---

## Architectural Decisions & Trade-offs

### Decision 1: Claude Haiku vs. Sonnet
- **Haiku:** 3-5x faster, 4x cheaper, 85% accuracy
- **Sonnet:** Slower, expensive, 95% accuracy

**Choice:** Default to Haiku, fallback to Sonnet on failures.

**Lesson:** Speed matters more than accuracy for rapid iterations. Fail fast, retry smart.

---

### Decision 2: DOM Parsing vs. Vision
- **DOM:** Fast, cheap, works for structured HTML
- **Vision:** Slow, expensive, works for canvas/images/complex layouts

**Choice:** Start with DOM, fallback to vision after 3 failures.

**Lesson:** Use the cheapest approach that works. Don't pay for GPT-4 Vision when HTML parsing suffices.

---

### Decision 3: Max 8 Actions vs. Max 20 Actions
- **20 actions:** Agent explores thoroughly (slow, expensive)
- **8 actions:** Forces faster decisions (risk of premature abort)

**Choice:** 8 actions. Fail fast, move on.

**Lesson:** In production, timeout thresholds prevent runaway costs. Set them based on 90th percentile, not worst case.

---

### Decision 4: Emergency Skip After 90s on Challenge 1
- Challenge 1 had popup hell that blocked everything
- Agent got stuck for 5+ minutes repeatedly
- Added nuclear option: force skip after 90s

**Choice:** Accept failure on hard challenges, keep moving.

**Lesson:** Production systems need circuit breakers. Don't let one bad input halt the entire pipeline.

---

## When to Use This Architecture

### ✅ Good Use Cases

**1. Exploratory Testing**
- Navigate unknown websites
- Find edge cases in UI flows
- Stress test dynamic interfaces

**2. Document Processing**
- Variable formats (PDFs, scans, handwriting)
- Unstructured data extraction
- Schema-less input

**3. Customer Support**
- Every query is different
- Can't script responses in advance
- Need reasoning, not retrieval

**4. Legacy System Migration**
- Undocumented behavior
- No API, only UI
- Screen scraping + reasoning

---

### ❌ Bad Use Cases

**1. Repetitive Tasks with Known Solutions**
- Daily reports, batch processing
- Known input/output pairs
- Use cron + scripts

**2. High-Volume, Low-Margin Operations**
- $0.15/run × 10,000 runs/day = $1,500/day
- Script cost: $0
- Use AI for exceptions, script for the norm

**3. Safety-Critical Systems (as primary)**
- Medical diagnosis, financial trading
- Use AI for suggestions, humans + deterministic code for decisions

---

## Cost Analysis: When Does AI Break Even?

### Scenario 1: Known Challenges (This Project)
- **AI Cost:** $0.15/run, 5 min/run
- **Script Cost:** $0/run, 30 sec/run
- **Break-even:** Never (script always wins)

### Scenario 2: Daily New Challenges
- **AI Cost:** $0.15/run, 5 min/run, no setup
- **Script Cost:** $0/run, 30 sec/run, 2 hours setup per challenge
- **Break-even:** 80 runs ($0.15 × 80 = $12 = 1 hour of eng time at $150/hr)

If challenge changes < every 80 runs → AI wins  
If challenge changes > every 80 runs → Script wins

### Scenario 3: 100 Variable Challenges
- **AI Cost:** $0.15 × 100 = $15, 500 minutes (8 hours), no setup
- **Script Cost:** 100 × 2 hours setup = 200 hours, then $0/run
- **Break-even:** 1,333 runs

If you'll run this < 1,333 times → AI wins  
If you'll run this > 1,333 times → Script wins

**The formula:** Break-even = (Script setup time × eng hourly rate) / (AI cost per run)

---

## Production Readiness Checklist

What's implemented:
- ✅ Multi-provider LLM abstraction
- ✅ Cost + performance metrics
- ✅ Timeout enforcement
- ✅ Graceful degradation
- ✅ Failure recovery (retries, skips)
- ✅ Modular architecture

What's missing for production:
- ❌ Structured logging (JSON logs to CloudWatch/Datadog)
- ❌ Distributed tracing (OpenTelemetry)
- ❌ Alerting (PagerDuty on 90% failure rate)
- ❌ Screenshot capture on failure (upload to S3)
- ❌ Rate limit handling with exponential backoff
- ❌ Authentication + secrets management
- ❌ Horizontal scaling (fleet of agents)
- ❌ Result deduplication + caching

---

## The Meta-Lesson: Engineering Judgment

**The question isn't:**
> "Can we build an AI agent for this?"

**The question is:**
> "What's the right tool for this job?"

Sometimes that's AI. Sometimes that's a 50-line Python script.

Knowing the difference—and designing systems that can use both—is engineering leadership.

---

## If I Were to Continue This Project

### Option A: Brute Force (2 hours)
1. Manually solve all 30 challenges
2. Document solutions in `SOLUTIONS.md`
3. Hardcode action sequences
4. Runtime: 30 seconds, Cost: $0, Reliability: 100%

### Option B: Hybrid Approach (4 hours)
1. Manually solve challenges, note patterns
2. Build challenge classifier (LLM analyzes challenge text → determines type)
3. Cache solutions for known patterns
4. Fall back to LLM reasoning for unknown patterns
5. Result: Best of both worlds

### Option C: Vision-First (6 hours)
1. Switch to vision models (Claude Sonnet with screenshots)
2. Agent sees page like a human
3. Might handle fake buttons better (visual distinction)
4. Cost: $0.30/run (2x current), possibly higher accuracy

### Option D: Walk Away (0 hours)
1. Recognize this is a toy problem
2. Use learnings for real production systems
3. Post insights on LinkedIn
4. Move on to actual impact

**My choice:** Option D. The architecture is the asset, not the solution to 30 puzzles.

---

## Key Takeaways for Engineering Leaders

1. **Cost-awareness:** Track tokens/run before scaling. $0.15 becomes $15,000 at 100k runs.

2. **Graceful degradation:** Always have a fallback. Text → Vision → Human escalation.

3. **Fail fast:** Timeouts prevent runaway costs. Set them based on P90, not worst case.

4. **Modular design:** Swap components without rewrites. Future-proof architecture.

5. **Know when to script:** If you can write 50 lines of Python, do that instead of $0.15/run LLM calls.

6. **Production ≠ Demo:** Metrics, logging, alerting aren't optional. They're how you survive 3am incidents.

7. **Engineering judgment:** The best solution isn't always the most sophisticated one.

---

## About the Author

Built by a Technical Program Manager with 12 years in autonomous vehicles (Luminar, Cruise, Uber ATG).

I've managed fleets of test vehicles, coordinated 600+ OEM demonstrations, and built testing infrastructure for safety-critical robotics.

The difference between a script and a system is operational thinking:
- What happens when it fails?
- How do you debug at 3am?
- How does it scale from 30 to 30,000?

This agent is designed with that mindset. Even if the "right" answer for this specific problem is a 50-line script.

---

**Repository:** [Link to GitHub]  
**Contact:** [LinkedIn/Email]  
**Built:** February 2026
