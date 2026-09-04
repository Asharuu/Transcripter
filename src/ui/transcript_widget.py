"""Transcript UI Widget: Renders turn-aggregated, editable speaker blocks."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QScrollArea,
    QFrame,
    QSizePolicy,
)

from src.core.speaker_manager import SpeakerTurn


class SpeakerTurnCard(QFrame):
    """A card representing a single speaker turn block in Hallmark Terminal aesthetic."""

    text_changed = Signal(int, str)  # turn_id, new_text

    def __init__(self, turn: SpeakerTurn, parent=None):
        super().__init__(parent)
        self.turn_id = turn.id
        self.speaker = turn.speaker
        self._init_ui(turn)

    def _init_ui(self, turn: SpeakerTurn):
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Determine speaker channel type
        is_local = "You" in self.speaker or "Speaker 1" in self.speaker or "MIC" in self.speaker.upper()
        if is_local:
            badge_text = "[ CH-01 // YOU ]" if ("You" in self.speaker or "Speaker 1" in self.speaker) else f"[ CH-01 // {self.speaker.upper()} ]"
            card_bg = "#101612"
            border_color = "#1f3326"
            badge_bg = "#092416"
            badge_fg = "#34d399"
            badge_border = "#10b981"
        else:
            badge_text = "[ CH-02 // SYSTEM ]" if ("Remote" in self.speaker or "Speaker 2" in self.speaker) else f"[ CH-02 // {self.speaker.upper()} ]"
            card_bg = "#141611"
            border_color = "#332714"
            badge_bg = "#241806"
            badge_fg = "#fbbf24"
            badge_border = "#d97706"

        self.setStyleSheet(f"""
            SpeakerTurnCard {{
                background-color: {card_bg};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 6px;
                margin-bottom: 6px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Header row: Monospace Channel Badge + Bracketed Telemetry Timestamp
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        # Speaker Badge (Phosphor Monospace Telemetry)
        self.badge = QLabel(badge_text)
        self.badge.setStyleSheet(f"""
            QLabel {{
                background-color: {badge_bg};
                color: {badge_fg};
                border: 1px solid {badge_border};
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.5px;
                padding: 2px 7px;
                border-radius: 3px;
            }}
        """)
        header_layout.addWidget(self.badge)

        # Timestamp info (bracketed technical format: [ 00:14 ])
        safe_time = max(0, int(turn.start_time))
        mins, secs = divmod(safe_time, 60)
        hours, mins = divmod(mins, 60)
        time_str = f"[ {hours:02d}:{mins:02d}:{secs:02d} ]" if hours > 0 else f"[ {mins:02d}:{secs:02d} ]"
        self.time_label = QLabel(time_str)
        self.time_label.setStyleSheet("""
            QLabel {
                color: #5f7e68;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                font-size: 11px;
                font-weight: 600;
            }
        """)
        header_layout.addWidget(self.time_label)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Editable Text Body (Crisp phosphor ink, clean line height)
        self.text_edit = QPlainTextEdit(turn.full_text)
        self.text_edit.setFont(QFont("Segoe UI", 11))
        self.text_edit.setStyleSheet("""
            QPlainTextEdit {
                background-color: transparent;
                color: #e0f2e5;
                border: none;
                padding: 0;
                line-height: 1.5;
            }
            QPlainTextEdit:focus {
                background-color: #0b0e0c;
                border: 1px solid #10b981;
                border-radius: 3px;
                padding: 6px;
                color: #ffffff;
            }
        """)
        self.text_edit.textChanged.connect(self._on_text_edited)
        self.text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self._adjust_height()
        layout.addWidget(self.text_edit)

    def _adjust_height(self):
        doc = self.text_edit.document()
        doc_height = int(doc.size().height())
        self.text_edit.setFixedHeight(max(40, doc_height + 15))

    def update_text(self, new_text: str):
        """Update text programmatically when new sentences arrive in the same turn."""
        if self.text_edit.toPlainText() != new_text:
            self.text_edit.blockSignals(True)
            self.text_edit.setPlainText(new_text)
            self.text_edit.blockSignals(False)
            self._adjust_height()

    def _on_text_edited(self):
        self._adjust_height()
        self.turn_edited_signal() if hasattr(self, 'turn_edited_signal') else None
        self.text_changed.emit(self.turn_id, self.text_edit.toPlainText())


class TranscriptViewWidget(QWidget):
    """Scrollable container that displays all speaker turn blocks."""

    turn_edited = Signal(int, str)  # turn_id, new_text

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cards: dict[int, SpeakerTurnCard] = {}
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll Area with Audiophile styling
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #0b0e0c;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #0b0e0c;
                width: 7px;
                margin: 0px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #232d27;
                min-height: 24px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #10b981;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # Container for cards
        self.container = QWidget()
        self.container.setStyleSheet("background-color: #0b0e0c;")
        self.cards_layout = QVBoxLayout(self.container)
        self.cards_layout.setContentsMargins(16, 16, 16, 16)
        self.cards_layout.setSpacing(10)
        self.cards_layout.addStretch()

        self.scroll_area.setWidget(self.container)
        main_layout.addWidget(self.scroll_area)

    def add_turn(self, turn: SpeakerTurn):
        """Add a new speaker turn card."""
        card = SpeakerTurnCard(turn)
        card.text_changed.connect(self._on_card_edited)
        self.cards[turn.id] = card

        # Insert before the stretch at the bottom
        insert_idx = max(0, self.cards_layout.count() - 1)
        self.cards_layout.insertWidget(insert_idx, card)
        self.scroll_to_bottom()

    def update_turn(self, turn: SpeakerTurn):
        """Update an existing speaker turn card."""
        if turn.id in self.cards:
            self.cards[turn.id].update_text(turn.full_text)
            self.scroll_to_bottom()

    def clear(self):
        """Remove all cards."""
        for card in self.cards.values():
            self.cards_layout.removeWidget(card)
            card.deleteLater()
        self.cards.clear()

    def _on_card_edited(self, turn_id: int, new_text: str):
        self.turn_edited.emit(turn_id, new_text)

    def scroll_to_bottom(self):
        vsb = self.scroll_area.verticalScrollBar()
        vsb.setValue(vsb.maximum())
