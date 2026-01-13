"""Game time management."""

from enum import Enum

import config


class GameMode(Enum):
    """Game time modes."""
    REAL_TIME = "real_time"
    TURN_BASED = "turn_based"


class TimeManager:
    """Manages game time and mode switching."""

    def __init__(self):
        self.game_mode = GameMode.REAL_TIME
        self.game_time = 480.0  # Start at 8:00 AM (in minutes from midnight)
        self.day = 1
        self.time_scale = config.TIME_SCALE
        self.paused = False

    def update(self, dt: float):
        """Update game time. dt is real-world seconds."""
        if self.paused or self.game_mode == GameMode.TURN_BASED:
            return

        # Convert real seconds to game minutes
        self.game_time += dt * self.time_scale

        # Handle day rollover
        if self.game_time >= config.MINUTES_PER_DAY:
            self.game_time -= config.MINUTES_PER_DAY
            self.day += 1

    def enter_conversation_mode(self):
        """Switch to turn-based mode for conversations."""
        self.game_mode = GameMode.TURN_BASED

    def exit_conversation_mode(self):
        """Return to real-time mode."""
        self.game_mode = GameMode.REAL_TIME

    def get_hour(self) -> int:
        """Get current hour (0-23)."""
        return int(self.game_time // 60)

    def get_minute(self) -> int:
        """Get current minute (0-59)."""
        return int(self.game_time % 60)

    def get_time_string(self) -> str:
        """Get formatted time string (HH:MM)."""
        return f"{self.get_hour():02d}:{self.get_minute():02d}"

    def get_time_of_day(self) -> str:
        """Get current time period."""
        hour = self.get_hour()
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"

    def is_daytime(self) -> bool:
        """Check if it's daytime (6 AM - 8 PM)."""
        hour = self.get_hour()
        return 6 <= hour < 20

    def toggle_pause(self):
        """Toggle pause state."""
        self.paused = not self.paused
