# LLMville - Developer Context for Claude

## Project Summary
2D social simulation where AI-powered NPCs have conversations, form relationships, and take actions. NPCs have personalities that affect dialogue and behavior.

## Architecture Overview

```
main.py                        → Entry point, initializes Game + DialogueManager
src/core/game.py               → Main loop, event handling, system orchestration
src/core/world.py              → 50x50 grid, terrain, A* pathfinding
src/entities/person.py         → NPC class: personality, relationships, inventory, CharacterState
src/interaction/dialogue_manager.py → Conversation orchestration (THREADED, non-blocking)
src/ai/claude_client.py        → Anthropic API wrapper (Haiku for dialogue, Sonnet for actions)
src/ai/prompt_builder.py       → Builds personality-aware prompts
src/ai/action_interpreter.py   → LLM extracts actions from dialogue (NEW)
src/ai/outcome_resolver.py     → LLM determines action success/effects (NEW)
src/systems/state_manager.py   → Applies effects to character state (NEW)
```

## Key Concepts

### Threading Model
- API calls run on background threads (ThreadPoolExecutor, max 3)
- Main game loop stays responsive during AI thinking
- All game state updates happen on main thread
- Check `DialogueManager.update()` each frame for completed responses

### Conversation Flow (Open-Ended Action System)
1. `ProximitySystem` detects adjacent NPCs
2. `Game.initiate_interaction()` checks willingness
3. `DialogueManager.initiate_conversation()` starts turn-based dialogue
4. After each message:
   - `ActionInterpreter` (LLM) extracts any action from natural dialogue
   - `OutcomeResolver` (LLM) determines success and effects
   - `StateManager` applies effects (health, conditions, gold, items)
   - Factual announcement shows centered on screen (only for state-changing actions)
5. Post-conversation: both NPCs generate reflections → relationship updates

### Character State (NEW)
- `Person.state.health_conditions`: List of descriptive injuries (e.g., "broken leg", "black eye")
- `Person.state.effective_move_speed`: Calculated from conditions (broken leg = 0.3x speed)
- Conditions affect what characters can do and appear in prompts

### Relationship System
- `feeling_score`: -1.0 (hostile) to +1.0 (close friend)
- Stored in `Person.relationships[other_name]`
- Each relationship has: feeling_score, interaction_count, history (summaries), notes (observations)
- Decays toward neutral without interaction

### Personality Traits (0-1 scale)
friendliness, honesty, greed, bravery, curiosity, patience
Defined in `config.py`, generated in `Person.Personality.generate_random()`

## File Locations for Common Tasks

| Task | File(s) |
|------|---------|
| Add personality trait | `config.py`, `person.py`, `prompt_builder.py` |
| Modify conversation prompts | `src/ai/prompt_builder.py` |
| Change conversation length | `config.py` → MAX_CONVERSATION_TURNS |
| Add new item type | `src/entities/item.py` |
| Modify NPC behavior | `src/systems/movement.py`, `proximity.py` |
| Adjust relationship logic | `src/systems/relationship.py` |
| Change world layout | `src/core/world.py` → `_generate_terrain()` |

## Gotchas & Notes

- **Rate limiting**: ClaudeClient has built-in rate limiter (50 req/min, 40k tokens/min)
- **Fallback dialogue**: API errors → "*trails off awkwardly*"
- **Cooldown**: 30 game minutes between same-pair interactions
- **Max turns**: 6 per participant (12 total messages) to prevent infinite convos
- **Time scale**: 1 real second = 1 game minute (configurable in config.py)
- **Dual models**: Haiku 4.5 for fast dialogue, Sonnet 4.5 for smarter action interpretation
- **Action optimization**: ActionInterpreter only calls LLM when `*action*` markers detected in dialogue

## Current State / TODOs

<!-- Update this section as you work -->
- [ ] (add current work items here)

## Recent Changes

- **Dual-model architecture**: Haiku 4.5 for dialogue (fast/cheap), Sonnet 4.5 for action engine (smarter)
- **Action interpreter optimization**: Only calls LLM when `*asterisk*` markers detected in dialogue
- **Slowed time scale**: Changed from 60x to 1x (1 real second = 1 game minute) so conversations make temporal sense
- **Open-ended action system**: Replaced explicit action tokens with LLM-based interpretation
- **Conservative action detection**: Only detects state-changing actions (attacks, trades, theft) - ignores mundane gestures
- **Descriptive health**: Added `CharacterState` with `health_conditions` list instead of just HP
- **Movement modifiers**: Conditions like "broken leg" slow movement via `effective_move_speed`
- **AI-generated narratives**: Outcome resolver generates natural narrative text with state changes
- **Dialogue/actions separated**: Dialogue shows only spoken words; `*actions*` stripped, outcomes shown inline
- **Conditions in UI**: Entity panel now shows health conditions with warning color
- **Character detail panel**: Press Tab for fullscreen character view, arrow keys to cycle through all characters
- **Comprehensive logging**: Terminal shows all dialogue, action interpretation, outcome resolution

## Decisions Made

- Using ThreadPoolExecutor for non-blocking API calls
- Relationships decay toward neutral to create dynamic social dynamics
- Post-conversation reflections generate lasting memories
- **Open-ended actions**: No predefined action categories - LLM interprets any natural action
- **LLM-based outcomes**: OutcomeResolver uses LLM to determine success/effects (no hardcoded rules)
- **Descriptive state**: health_conditions are free-form strings rather than numeric stats
- **Dual-model strategy**: Cheap/fast model (Haiku) for dialogue, smart model (Sonnet) for action interpretation
- **Lazy action detection**: Skip LLM call entirely if no `*action*` markers in dialogue (saves cost/latency)

---
*Keep this file updated when making significant changes to help future sessions.*
