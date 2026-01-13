"""Anthropic API wrapper with rate limiting."""

import time
import threading
from collections import deque

from anthropic import Anthropic

import config


class RateLimiter:
    """Thread-safe rate limiter for API calls."""

    def __init__(self, requests_per_minute: int, tokens_per_minute: int):
        self.rpm = requests_per_minute
        self.tpm = tokens_per_minute
        self.request_times: deque = deque()
        self.token_usage: deque = deque()
        self.lock = threading.Lock()

    def acquire(self, estimated_tokens: int = 500):
        """Wait until rate limit allows another request (blocking)."""
        while True:
            with self.lock:
                now = time.time()

                # Clean old entries (older than 60 seconds)
                while self.request_times and now - self.request_times[0] > 60:
                    self.request_times.popleft()
                while self.token_usage and now - self.token_usage[0][0] > 60:
                    self.token_usage.popleft()

                # Check request limit
                if len(self.request_times) >= self.rpm:
                    wait_time = 60 - (now - self.request_times[0])
                    if wait_time > 0:
                        time.sleep(min(wait_time, 1.0))
                        continue

                # Check token limit
                current_tokens = sum(t[1] for t in self.token_usage)
                if current_tokens + estimated_tokens > self.tpm:
                    if self.token_usage:
                        wait_time = 60 - (now - self.token_usage[0][0])
                        if wait_time > 0:
                            time.sleep(min(wait_time, 1.0))
                            continue

                self.request_times.append(time.time())
                return

    def record_usage(self, tokens: int):
        """Record actual token usage after response."""
        with self.lock:
            self.token_usage.append((time.time(), tokens))


class ClaudeClient:
    """Wrapper for Anthropic API with synchronous methods for threading."""

    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.model = config.CLAUDE_MODEL
        self.rate_limiter = RateLimiter(
            requests_per_minute=config.API_REQUESTS_PER_MINUTE,
            tokens_per_minute=config.API_TOKENS_PER_MINUTE
        )

    def generate_dialogue_sync(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        max_tokens: int = 300
    ) -> str:
        """Generate a single dialogue response (synchronous, for use in threads)."""
        self.rate_limiter.acquire(estimated_tokens=max_tokens)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages
            )

            # Record actual usage
            usage = response.usage
            self.rate_limiter.record_usage(usage.input_tokens + usage.output_tokens)

            return response.content[0].text

        except Exception as e:
            print(f"Claude API error: {e}")
            return "*trails off awkwardly*"

    def generate_conversation_summary_sync(
        self,
        conversation_history: list[dict[str, str]],
        speaker_name: str,
        other_name: str
    ) -> dict:
        """Generate a summary of the conversation (synchronous)."""
        self.rate_limiter.acquire(estimated_tokens=200)

        system_prompt = f"""You are summarizing a conversation from {speaker_name}'s perspective.
Analyze the conversation and provide:
1. A brief 1-sentence summary
2. A relationship_delta between -0.3 and 0.3 based on how positive/negative the interaction was
3. An optional memorable detail to remember about {other_name}

Respond in this exact format:
SUMMARY: [your summary]
DELTA: [number between -0.3 and 0.3]
NOTE: [memorable detail or "none"]"""

        # Format conversation for context
        conv_text = "\n".join([
            f"{m['role'].title()}: {m['content']}"
            for m in conversation_history
        ])

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=150,
                system=system_prompt,
                messages=[{"role": "user", "content": f"Summarize this conversation:\n\n{conv_text}"}]
            )

            text = response.content[0].text
            return self._parse_summary_response(text)

        except Exception as e:
            print(f"Summary generation error: {e}")
            return {
                "summary": "Had a conversation",
                "delta": 0.0,
                "note": None
            }

    def _parse_summary_response(self, text: str) -> dict:
        """Parse the summary response."""
        result = {
            "summary": "Had a conversation",
            "delta": 0.0,
            "note": None
        }

        lines = text.strip().split("\n")
        for line in lines:
            if line.startswith("SUMMARY:"):
                result["summary"] = line[8:].strip()
            elif line.startswith("DELTA:"):
                try:
                    delta = float(line[6:].strip())
                    result["delta"] = max(-0.3, min(0.3, delta))
                except ValueError:
                    pass
            elif line.startswith("NOTE:"):
                note = line[5:].strip()
                if note.lower() != "none":
                    result["note"] = note

        return result

    def generate_reflection_sync(self, reflection_prompt: str) -> dict:
        """Generate a post-conversation reflection (synchronous).

        Args:
            reflection_prompt: The full reflection prompt from PromptBuilder

        Returns:
            Dict with 'summary', 'delta', and 'observation' keys
        """
        self.rate_limiter.acquire(estimated_tokens=200)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                system="You are reflecting on a conversation you just had. Follow the format exactly.",
                messages=[{"role": "user", "content": reflection_prompt}]
            )

            text = response.content[0].text
            usage = response.usage
            self.rate_limiter.record_usage(usage.input_tokens + usage.output_tokens)

            return self._parse_reflection_response(text)

        except Exception as e:
            print(f"Reflection generation error: {e}")
            return {
                "summary": "Had a conversation",
                "delta": 0.05,
                "observation": None
            }

    def _parse_reflection_response(self, text: str) -> dict:
        """Parse the reflection response format."""
        result = {
            "summary": "Had a conversation",
            "delta": 0.0,
            "observation": None
        }

        lines = text.strip().split("\n")
        for line in lines:
            if line.startswith("SUMMARY:"):
                result["summary"] = line[8:].strip()
            elif line.startswith("FEELING:"):
                try:
                    delta = float(line[8:].strip())
                    result["delta"] = max(-0.3, min(0.3, delta))
                except ValueError:
                    pass
            elif line.startswith("OBSERVATION:"):
                obs = line[12:].strip()
                if obs.lower() not in ("nothing notable", "none", "n/a"):
                    result["observation"] = obs

        return result
