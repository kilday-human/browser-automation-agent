#!/usr/bin/env python3
"""
Browser Automation Agent for Brett Adcock's Challenge
Solves 30 web challenges in under 5 minutes.

Usage:
    python main.py                          # Run with defaults (Anthropic, headless)
    python main.py --provider openai        # Use OpenAI
    python main.py --visible                # Show browser window
    python main.py --timeout 180            # Custom timeout (seconds)
"""

import argparse
import os
import sys
import signal
from dotenv import load_dotenv

from agent import run_challenge


def timeout_handler(signum, frame):
    """Hard timeout handler - kills process if soft timeout fails."""
    print("\n⏰ HARD TIMEOUT REACHED - Force killing process")
    sys.exit(2)


def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description="Browser automation agent for web challenge solving",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai"],
        default="anthropic",
        help="LLM provider (default: anthropic)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Specific model to use (default: provider's default)",
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Show browser window (default: headless)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout in seconds (default: 300 = 5 minutes)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="run_stats.json",
        help="Output file for run statistics (default: run_stats.json)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output",
    )
    parser.add_argument(
        "--no-vision",
        action="store_true",
        help="Disable vision fallback for stuck challenges",
    )
    
    args = parser.parse_args()
    
    # Validate API keys
    if args.provider == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("Set it with: export ANTHROPIC_API_KEY=your-key-here")
        sys.exit(1)
    elif args.provider == "openai" and not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Set it with: export OPENAI_API_KEY=your-key-here")
        sys.exit(1)
    
    try:
        # Set hard timeout (enforced by OS signal)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(args.timeout + 10)  # Add 10s buffer for cleanup
        print(f"Hard timeout set: {args.timeout + 10}s")
        
        metrics = run_challenge(
            provider=args.provider,
            model=args.model,
            headless=not args.visible,
            timeout=args.timeout,
            output_file=args.output,
            verbose=not args.quiet,
            use_vision_fallback=not args.no_vision,
        )
        
        # Exit code based on success
        if metrics.aborted:
            sys.exit(2)
        elif metrics.total_challenges_completed < 30:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\nAborted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
