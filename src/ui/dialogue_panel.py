"""Dialogue panel for viewing conversations."""

import pygame
from typing import Optional

import config
from ..ai.conversation import Conversation


class DialoguePanel:
    """Panel for displaying active conversations."""

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.visible = False
        self.conversation: Optional[Conversation] = None

        # Panel dimensions
        self.width = 550
        self.height = 320
        self.x = (config.WINDOW_WIDTH - self.width) // 2
        self.y = config.WINDOW_HEIGHT - self.height - 20

        # Colors - high contrast for readability
        self.bg_color = (25, 25, 35)  # Dark blue-gray
        self.border_color = (80, 80, 100)
        self.title_bg_color = (40, 40, 55)
        self.message_bg_color = (35, 35, 50)
        self.text_color = (240, 240, 240)  # Bright white
        self.speaker_a_color = (100, 200, 255)  # Light blue
        self.speaker_b_color = (255, 180, 100)  # Orange
        self.dim_text_color = (150, 150, 170)

        # Fonts
        pygame.font.init()
        self.font_title = pygame.font.Font(None, 26)
        self.font_name = pygame.font.Font(None, 22)
        self.font_message = pygame.font.Font(None, 20)

        # Pixel-based scrolling
        self.scroll_y = 0  # Pixel offset from top
        self.scroll_speed = 30  # Pixels per scroll tick
        self.content_height = 0  # Total height of all messages
        self.user_scrolled = False  # Track if user manually scrolled

        # Message area dimensions
        self.msg_area_height = self.height - 70

    def show(self, conversation: Conversation):
        """Show the panel with a conversation."""
        self.conversation = conversation
        self.visible = True
        self.user_scrolled = False
        # Calculate content and scroll to bottom
        self._calculate_content_height()
        self._scroll_to_bottom()

    def hide(self):
        """Hide the panel."""
        self.visible = False
        self.conversation = None

    def toggle(self, conversation: Optional[Conversation] = None):
        """Toggle panel visibility."""
        if self.visible and (conversation is None or conversation == self.conversation):
            self.hide()
        elif conversation:
            self.show(conversation)

    def _calculate_content_height(self):
        """Calculate total height of all messages."""
        if not self.conversation:
            self.content_height = 0
            return

        messages = self.conversation.get_display_messages()
        total_height = 10  # Initial padding

        for msg in messages:
            total_height += self._get_message_height(msg)

        self.content_height = total_height

    def _get_message_height(self, msg: dict) -> int:
        """Calculate the height of a single message."""
        height = 24  # Name line height

        # Calculate wrapped text height
        content = msg["content"]
        max_width = self.width - 80  # Account for padding and scrollbar
        words = content.split()
        lines = []
        current_line = []

        for word in words:
            current_line.append(word)
            test_line = ' '.join(current_line)
            if self.font_message.size(test_line)[0] > max_width:
                if len(current_line) > 1:
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(test_line)
                    current_line = []

        if current_line:
            lines.append(' '.join(current_line))

        height += len(lines) * 18  # Line height
        height += 12  # Spacing after message

        return height

    def _scroll_to_bottom(self):
        """Scroll to the bottom of the content."""
        max_scroll = max(0, self.content_height - self.msg_area_height + 20)
        self.scroll_y = max_scroll

    def render(self):
        """Render the dialogue panel."""
        if not self.visible or not self.conversation:
            return

        # Main panel background with shadow
        shadow_rect = pygame.Rect(self.x + 4, self.y + 4, self.width, self.height)
        pygame.draw.rect(self.screen, (0, 0, 0, 100), shadow_rect, border_radius=10)

        panel_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(self.screen, self.bg_color, panel_rect, border_radius=10)
        pygame.draw.rect(self.screen, self.border_color, panel_rect, 2, border_radius=10)

        # Title bar
        title_rect = pygame.Rect(self.x, self.y, self.width, 40)
        pygame.draw.rect(self.screen, self.title_bg_color, title_rect,
                        border_top_left_radius=10, border_top_right_radius=10)

        # Title text
        title = f"{self.conversation.participant_a.name} & {self.conversation.participant_b.name}"
        title_surface = self.font_title.render(title, True, self.text_color)
        self.screen.blit(title_surface, (self.x + 15, self.y + 10))

        # Close hint
        close_hint = self.font_message.render("ESC to close | Scroll to navigate", True, self.dim_text_color)
        self.screen.blit(close_hint, (self.x + self.width - 200, self.y + 12))

        # Messages area
        msg_y = self.y + 50
        msg_area = pygame.Rect(self.x + 10, msg_y, self.width - 20, self.msg_area_height)

        # Message area background
        pygame.draw.rect(self.screen, self.message_bg_color, msg_area, border_radius=5)

        # Clip messages to area
        self.screen.set_clip(msg_area)

        # Render messages with pixel offset
        messages = self.conversation.get_display_messages()
        y_pos = msg_y + 10 - self.scroll_y

        for msg in messages:
            msg_height = self._get_message_height(msg)

            # Only render if visible
            if y_pos + msg_height > msg_y and y_pos < msg_y + self.msg_area_height:
                # Determine speaker color
                if msg["speaker"] == self.conversation.participant_a.name:
                    speaker_color = self.speaker_a_color
                else:
                    speaker_color = self.speaker_b_color

                self._render_message(msg, self.x + 20, y_pos, speaker_color)

            y_pos += msg_height

        # Reset clip
        self.screen.set_clip(None)

        # Render scrollbar if needed
        if self.content_height > self.msg_area_height:
            self._render_scrollbar()

        # Waiting indicator if conversation is still going
        if self.conversation.is_active():
            waiting_text = "Waiting for response..."
            waiting_surface = self.font_message.render(waiting_text, True, self.dim_text_color)
            self.screen.blit(waiting_surface, (self.x + 15, self.y + self.height - 22))

    def _render_message(self, msg: dict, x: int, y: int, speaker_color: tuple) -> int:
        """Render a single message. Returns the y position for the next message."""
        # Speaker name with colored background pill
        name = msg["speaker"].split()[0]  # First name only
        name_surface = self.font_name.render(name, True, speaker_color)
        name_width = name_surface.get_width()

        # Name background
        name_bg_rect = pygame.Rect(x - 5, y - 2, name_width + 10, 20)
        bg_color = tuple(c // 4 for c in speaker_color)  # Darker version
        pygame.draw.rect(self.screen, bg_color, name_bg_rect, border_radius=3)

        self.screen.blit(name_surface, (x, y))
        y += 24

        # Message text (wrap long messages)
        content = msg["content"]
        max_width = self.width - 80
        words = content.split()
        lines = []
        current_line = []

        for word in words:
            current_line.append(word)
            test_line = ' '.join(current_line)
            if self.font_message.size(test_line)[0] > max_width:
                if len(current_line) > 1:
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(test_line)
                    current_line = []

        if current_line:
            lines.append(' '.join(current_line))

        for line in lines:
            text_surface = self.font_message.render(line, True, self.text_color)
            self.screen.blit(text_surface, (x + 5, y))
            y += 18

        return y + 12  # Add spacing between messages

    def _render_scrollbar(self):
        """Render a visual scrollbar."""
        # Scrollbar dimensions
        scrollbar_width = 8
        scrollbar_x = self.x + self.width - scrollbar_width - 15
        scrollbar_y = self.y + 55
        scrollbar_height = self.msg_area_height - 10

        # Track background
        track_rect = pygame.Rect(scrollbar_x, scrollbar_y, scrollbar_width, scrollbar_height)
        pygame.draw.rect(self.screen, (50, 50, 60), track_rect, border_radius=4)

        # Calculate thumb size and position
        visible_ratio = self.msg_area_height / self.content_height
        thumb_height = max(20, int(scrollbar_height * visible_ratio))

        max_scroll = max(1, self.content_height - self.msg_area_height + 20)
        scroll_ratio = self.scroll_y / max_scroll
        thumb_y = scrollbar_y + int((scrollbar_height - thumb_height) * scroll_ratio)

        # Thumb
        thumb_rect = pygame.Rect(scrollbar_x, thumb_y, scrollbar_width, thumb_height)
        thumb_color = (120, 120, 140) if not self.user_scrolled else (150, 150, 180)
        pygame.draw.rect(self.screen, thumb_color, thumb_rect, border_radius=4)

    def handle_scroll(self, direction: int):
        """Handle scroll input. direction: -1 for up, 1 for down."""
        if not self.conversation:
            return

        # Recalculate content height in case new messages arrived
        self._calculate_content_height()

        max_scroll = max(0, self.content_height - self.msg_area_height + 20)
        new_scroll = self.scroll_y + (direction * self.scroll_speed)
        new_scroll = max(0, min(max_scroll, new_scroll))

        # If user scrolls up from the bottom, mark as user-scrolled
        if new_scroll < max_scroll - 5:  # Small threshold
            self.user_scrolled = True
        # If user scrolls back to bottom, resume auto-scroll
        elif new_scroll >= max_scroll - 5:
            self.user_scrolled = False

        self.scroll_y = new_scroll

    def is_point_inside(self, x: int, y: int) -> bool:
        """Check if a point is inside the panel."""
        if not self.visible:
            return False
        return (self.x <= x <= self.x + self.width and
                self.y <= y <= self.y + self.height)

    def update(self):
        """Update the panel (auto-scroll to latest message if user hasn't scrolled)."""
        if self.conversation and self.visible:
            self._calculate_content_height()
            if not self.user_scrolled:
                self._scroll_to_bottom()
