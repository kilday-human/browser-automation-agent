# LinkedIn Post: When AI Doesn't Know What to Ignore

---

**When AI Doesn't Know What to Ignore**

I spent a weekend building an autonomous browser agent for automation challenges. The code worked beautifully. The architecture was solid. But here's what I learned about when NOT to use AI.

**The Challenge:**
Solve 30 browser puzzles in under 5 minutes. Popups, fake buttons, hidden elements, scroll-to-reveal codes. Classic UI testing nightmare.

**My AI Agent Approach:**
- Multi-LLM support (Claude, GPT-4, with vision fallback)
- DOM parsing + adaptive retry logic  
- Modular architecture with metrics/observability
- Cost per run: ~$0.15 | Time: ~5 minutes

**The "Right" Approach:**
```python
# Manually solve once, hardcode solutions
SOLUTIONS = {1: ["click_start", "wait"], 2: ["dismiss_popups", "type_code"]...}
# Cost: $0 | Time: 30 seconds | Reliability: 100%
```

**The Insight:**

AI agents excel at *reasoning about what to do*. They struggle with *knowing what to ignore*.

My agent had to learn—expensively—that:
- "Close" buttons can be fake decoys
- Cookie banners block everything
- Some scroll distances matter, others don't
- Certain text is instructions, other text is misdirection

A hardcoded script ignores all that by design. It just executes the known path.

**This is the automation paradox:**
- ✅ Known, stable environments → Scripts win
- ✅ Unknown, variable environments → AI wins  
- ✅ Production systems → Hybrid wins

**For Engineering Leaders:**

Don't deploy LLMs where deterministic code works. Use them where the environment is too variable to script:
- Customer support (every query is different)
- Document analysis (formats vary wildly)  
- Exploratory testing (finding unknown unknowns)
- Legacy system migration (undocumented behavior)

Save the $0.15 per run for problems where you *can't write the script in advance*.

**What I Built Shows:**

The value wasn't solving 30 scripted puzzles. It was building infrastructure that handles:
- Multi-provider abstraction (swap models instantly)
- Graceful degradation (text → vision fallback)
- Metrics + observability (cost tracking, performance monitoring)
- Failure recovery (timeouts, retries, emergency skips)

That's production thinking. That's what scales from 30 to 30,000.

---

**The meta-lesson:** Knowing when NOT to use AI is as important as knowing how to build with it.

Code + architecture details: [GitHub repo]

What problems are you tackling where AI actually makes sense vs. where it's overkill?

#AI #Engineering #BrowserAutomation #TPM #ArchitecturalDecisions

---

