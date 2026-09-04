"""Speaker Turn Manager: Aggregates continuous speech segments into cohesive speaker blocks."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable
import time


@dataclass
class SpeakerTurn:
    id: int
    speaker: str
    start_time: float
    end_time: float
    texts: list[str] = field(default_factory=list)
    is_finalized: bool = False

    @property
    def full_text(self) -> str:
        """Returns clean joined text with proper spacing."""
        return " ".join(t.strip() for t in self.texts if t.strip())

    def update_text(self, new_text: str) -> None:
        """Directly edits the full text of this turn (used in interactive UI editing)."""
        self.texts = [new_text.strip()]


class SpeakerTurnManager:
    """State machine that groups speech segments by speaker turns.
    
    Prevents fragmentation when the same speaker pauses and continues speaking.
    """

    def __init__(self):
        self.turns: list[SpeakerTurn] = []
        self.active_turn: SpeakerTurn | None = None
        self._next_id: int = 1

        # Event callbacks (used by UI to update live views)
        self.on_turn_created: Callable[[SpeakerTurn], None] | None = None
        self.on_turn_updated: Callable[[SpeakerTurn], None] | None = None
        self.on_turn_finalized: Callable[[SpeakerTurn], None] | None = None

    def add_segment(self, speaker: str, text: str, start_time: float, end_time: float) -> SpeakerTurn:
        """Process a newly transcribed speech segment.
        
        If the speaker matches the active turn, append text to the existing block.
        If a different speaker speaks, finalize the active block and open a new one.
        """
        clean_text = text.strip()
        if not clean_text:
            return self.active_turn

        if self.active_turn and self.active_turn.speaker == speaker and not self.active_turn.is_finalized:
            # SAME SPEAKER: Merge into current turn block
            self.active_turn.texts.append(clean_text)
            self.active_turn.end_time = max(self.active_turn.end_time, end_time)
            if self.on_turn_updated:
                self.on_turn_updated(self.active_turn)
            return self.active_turn
        else:
            # NEW SPEAKER or FIRST SPEAKER: Finalize previous turn if open
            if self.active_turn and not self.active_turn.is_finalized:
                self.active_turn.is_finalized = True
                if self.on_turn_finalized:
                    self.on_turn_finalized(self.active_turn)

            # Create new turn
            new_turn = SpeakerTurn(
                id=self._next_id,
                speaker=speaker,
                start_time=start_time,
                end_time=end_time,
                texts=[clean_text],
                is_finalized=False,
            )
            self._next_id += 1
            self.turns.append(new_turn)
            self.active_turn = new_turn

            if self.on_turn_created:
                self.on_turn_created(new_turn)
            return new_turn

    def finalize_active_turn(self) -> None:
        """Finalize the currently active turn (e.g. when recording stops)."""
        if self.active_turn and not self.active_turn.is_finalized:
            self.active_turn.is_finalized = True
            if self.on_turn_finalized:
                self.on_turn_finalized(self.active_turn)
            self.active_turn = None

    def reset(self) -> None:
        """Reset the manager for a new recording session."""
        self.turns.clear()
        self.active_turn = None
        self._next_id = 1

    def format_duration(self, seconds: float) -> str:
        mins, secs = divmod(int(seconds), 60)
        hours, mins = divmod(mins, 60)
        if hours > 0:
            return f"{hours:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"

    def to_markdown(self, title: str, start_dt: datetime, duration_sec: float) -> str:
        """Export turns as clean Markdown following the product specification."""
        self.finalize_active_turn()
        dur_str = self.format_duration(duration_sec)
        date_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            f"# {title}",
            "",
            f"**Date & Time:** {date_str}  ",
            f"**Duration:** {dur_str}",
            "",
            "## Transcript",
            "",
        ]

        for turn in self.turns:
            lines.append(f"### {turn.speaker}")
            lines.append(f"{turn.full_text}")
            lines.append("")

        return "\n".join(lines).strip() + "\n"

    def to_plain_text(self, title: str, start_dt: datetime, duration_sec: float) -> str:
        """Export turns as simple formatted Plain Text."""
        self.finalize_active_turn()
        dur_str = self.format_duration(duration_sec)
        date_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            title,
            "=" * len(title),
            f"Date & Time: {date_str}",
            f"Duration: {dur_str}",
            "-" * 40,
            "",
        ]

        for turn in self.turns:
            lines.append(f"{turn.speaker}:")
            lines.append(f"{turn.full_text}")
            lines.append("")

        return "\n".join(lines).strip() + "\n"
