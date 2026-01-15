"""Social Simulation Game - Entry Point."""

import logging
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

from src.core.game import Game


def setup_logging():
    """Configure logging for dialogue and action debugging."""
    # Create formatter
    formatter = logging.Formatter('%(message)s')

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Set up loggers for our modules
    for logger_name in ['dialogue_manager', 'action_interpreter', 'outcome_resolver', 'state_manager']:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)  # INFO for normal use, DEBUG for verbose
        logger.addHandler(console_handler)
        logger.propagate = False  # Don't duplicate to root logger


def main():
    """Main entry point."""
    # Load environment variables
    load_dotenv()

    # Set up logging for debugging
    setup_logging()

    # Check for API key (optional - game works without AI)
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Note: ANTHROPIC_API_KEY not found in environment.")
        print("Running without AI conversations (entities will have simulated interactions).")
        print("To enable AI, create a .env file with: ANTHROPIC_API_KEY=your_key_here")
        print()

    # Create and run game
    game = Game()

    # Set up AI dialogue manager if API key available
    if api_key:
        try:
            from src.ai.claude_client import ClaudeClient
            from src.ai.prompt_builder import PromptBuilder
            from src.interaction.dialogue_manager import DialogueManager

            claude_client = ClaudeClient(api_key)
            prompt_builder = PromptBuilder()
            dialogue_manager = DialogueManager(
                claude_client=claude_client,
                prompt_builder=prompt_builder,
                entity_manager=game.entity_manager,
                time_manager=game.time_manager,
                relationship_system=game.relationship_system
            )
            game.set_dialogue_manager(dialogue_manager)
            print("AI conversations enabled!")
        except ImportError as e:
            print(f"Could not initialize AI system: {e}")
            print("Running without AI conversations.")

    print()
    print("=== Social Simulation ===")
    print("Controls:")
    print("  WASD/Arrows - Move camera")
    print("  Click       - Select entity")
    print("  Space       - Pause/Resume")
    print("  Escape      - Quit")
    print()

    game.run()


if __name__ == "__main__":
    main()
