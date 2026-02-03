"""Metrics tracking for challenge runs."""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ChallengeMetrics:
    number: int
    start_time: float
    end_time: Optional[float] = None
    actions_taken: int = 0
    llm_calls: int = 0
    success: bool = False
    error: Optional[str] = None

    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0

    def to_dict(self) -> dict:
        return {
            "challenge": self.number,
            "duration_ms": round(self.duration_ms, 2),
            "actions_taken": self.actions_taken,
            "llm_calls": self.llm_calls,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class RunMetrics:
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    challenges: list[ChallengeMetrics] = field(default_factory=list)
    total_challenges_completed: int = 0
    aborted: bool = False
    abort_reason: Optional[str] = None

    @property
    def total_duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return (time.time() - self.start_time) * 1000

    @property
    def total_duration_seconds(self) -> float:
        return self.total_duration_ms / 1000

    def start_challenge(self, number: int) -> ChallengeMetrics:
        metrics = ChallengeMetrics(number=number, start_time=time.time())
        self.challenges.append(metrics)
        return metrics

    def complete_challenge(self, metrics: ChallengeMetrics, success: bool = True, error: str = None):
        metrics.end_time = time.time()
        metrics.success = success
        metrics.error = error
        if success:
            self.total_challenges_completed += 1

    def finish(self, aborted: bool = False, reason: str = None):
        self.end_time = time.time()
        self.aborted = aborted
        self.abort_reason = reason

    def to_dict(self, llm_stats: dict = None) -> dict:
        return {
            "run_timestamp": datetime.fromtimestamp(self.start_time).isoformat(),
            "total_duration_seconds": round(self.total_duration_seconds, 2),
            "total_duration_ms": round(self.total_duration_ms, 2),
            "challenges_completed": self.total_challenges_completed,
            "challenges_attempted": len(self.challenges),
            "aborted": self.aborted,
            "abort_reason": self.abort_reason,
            "llm_stats": llm_stats or {},
            "challenges": [c.to_dict() for c in self.challenges],
        }

    def save(self, filepath: str, llm_stats: dict = None):
        with open(filepath, "w") as f:
            json.dump(self.to_dict(llm_stats), f, indent=2)

    def print_summary(self, llm_stats: dict = None):
        print("\n" + "=" * 60)
        print("RUN SUMMARY")
        print("=" * 60)
        print(f"Total Time:        {self.total_duration_seconds:.2f}s ({self.total_duration_ms:.0f}ms)")
        print(f"Challenges:        {self.total_challenges_completed}/{len(self.challenges)} completed")
        print(f"Status:            {'ABORTED - ' + self.abort_reason if self.aborted else 'FINISHED'}")
        
        if llm_stats:
            print(f"\nLLM Usage:")
            print(f"  Total Calls:     {llm_stats.get('total_calls', 0)}")
            print(f"  Input Tokens:    {llm_stats.get('total_input_tokens', 0):,}")
            print(f"  Output Tokens:   {llm_stats.get('total_output_tokens', 0):,}")
            print(f"  Estimated Cost:  ${llm_stats.get('total_cost', 0):.4f}")
            
            # Cost efficiency
            if self.total_challenges_completed > 0:
                cost_per_challenge = llm_stats.get('total_cost', 0) / self.total_challenges_completed
                print(f"  Cost/Challenge:  ${cost_per_challenge:.4f}")
        
        print("\nPer-Challenge Breakdown:")
        for c in self.challenges:
            status = "✓" if c.success else "✗"
            print(f"  {status} Challenge {c.number}: {c.duration_ms:.0f}ms, {c.actions_taken} actions, {c.llm_calls} LLM calls")
        
        # Identify slowest challenges
        if self.challenges:
            sorted_by_time = sorted(self.challenges, key=lambda x: x.duration_ms, reverse=True)
            print(f"\nSlowest Challenges:")
            for c in sorted_by_time[:5]:
                print(f"  Challenge {c.number}: {c.duration_ms:.0f}ms")
        
        print("=" * 60)
