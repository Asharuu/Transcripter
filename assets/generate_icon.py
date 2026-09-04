"""Generate professional application icons (PNG and ICO) for Transcripter."""

import os
from pathlib import Path
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QImage,
    QPainter,
    QColor,
    QPen,
    QLinearGradient,
    QRadialGradient,
    QPainterPath,
)
from PySide6.QtWidgets import QApplication
import sys


def generate_icon(size: int = 256) -> QImage:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

    scale = size / 256.0

    # 1. Background Rounded Squircle with Subtle Gradient
    bg_path = QPainterPath()
    margin = 8.0 * scale
    rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    bg_path.addRoundedRect(rect, 48.0 * scale, 48.0 * scale)

    # Background gradient: deep obsidian into deep forest emerald
    bg_gradient = QLinearGradient(0, 0, size, size)
    bg_gradient.setColorAt(0.0, QColor("#0d1410"))
    bg_gradient.setColorAt(0.5, QColor("#080c09"))
    bg_gradient.setColorAt(1.0, QColor("#040805"))

    painter.fillPath(bg_path, bg_gradient)

    # Outer Border: subtle emerald outline
    border_pen = QPen(QColor("#10b981"), 3.0 * scale)
    painter.setPen(border_pen)
    painter.drawPath(bg_path)

    # Inner glow
    glow_path = QPainterPath()
    glow_margin = 12.0 * scale
    glow_path.addRoundedRect(
        QRectF(glow_margin, glow_margin, size - 2 * glow_margin, size - 2 * glow_margin),
        44.0 * scale,
        44.0 * scale,
    )
    glow_pen = QPen(QColor(16, 185, 129, 45), 1.5 * scale)
    painter.setPen(glow_pen)
    painter.drawPath(glow_path)

    # 2. Central Waveform Soundwaves & Microphone
    # Center is at (128, 128) scaled
    cx = size / 2.0
    cy = size / 2.0 - 4.0 * scale

    # Modern Stylized Microphone Body
    mic_w = 34.0 * scale
    mic_h = 60.0 * scale
    mic_rect = QRectF(cx - mic_w / 2, cy - mic_h / 2, mic_w, mic_h)

    mic_path = QPainterPath()
    mic_path.addRoundedRect(mic_rect, mic_w / 2, mic_w / 2)

    # Microphone gradient: bright emerald to vibrant mint
    mic_gradient = QLinearGradient(cx, cy - mic_h / 2, cx, cy + mic_h / 2)
    mic_gradient.setColorAt(0.0, QColor("#34d399"))
    mic_gradient.setColorAt(1.0, QColor("#059669"))
    painter.fillPath(mic_path, mic_gradient)

    # Microphone mesh lines (subtle details)
    painter.setPen(QPen(QColor("#041a0e"), 2.0 * scale))
    painter.drawLine(
        QPointF(cx - mic_w / 2 + 4 * scale, cy - 8 * scale),
        QPointF(cx + mic_w / 2 - 4 * scale, cy - 8 * scale),
    )
    painter.drawLine(
        QPointF(cx - mic_w / 2 + 4 * scale, cy),
        QPointF(cx + mic_w / 2 - 4 * scale, cy),
    )

    # Microphone Outer Arc (cradle / pickup arc)
    arc_pen = QPen(QColor("#ffffff"), 4.0 * scale)
    arc_pen.setCapStyle(Qt.RoundCap)
    painter.setPen(arc_pen)

    arc_w = 60.0 * scale
    arc_h = 56.0 * scale
    arc_rect = QRectF(cx - arc_w / 2, cy - 14 * scale, arc_w, arc_h)
    # Draw arc from 0 to -180 degrees (bottom half)
    painter.drawArc(arc_rect, 0 * 16, -180 * 16)

    # Stand Stem & Base
    stem_top = cy - 14 * scale + arc_h
    stem_bottom = stem_top + 18 * scale
    painter.drawLine(QPointF(cx, stem_top), QPointF(cx, stem_bottom))

    base_w = 42.0 * scale
    painter.drawLine(
        QPointF(cx - base_w / 2, stem_bottom),
        QPointF(cx + base_w / 2, stem_bottom),
    )

    # 3. Dynamic Waveform Bars flanking the mic
    bars = [
        (-48.0 * scale, 24.0 * scale),
        (-64.0 * scale, 38.0 * scale),
        (-80.0 * scale, 20.0 * scale),
        (48.0 * scale, 24.0 * scale),
        (64.0 * scale, 38.0 * scale),
        (80.0 * scale, 20.0 * scale),
    ]

    wave_pen = QPen()
    wave_pen.setWidthF(4.0 * scale)
    wave_pen.setCapStyle(Qt.RoundCap)

    for offset_x, bar_h in bars:
        alpha = int(255 * (1.0 - abs(offset_x) / (100.0 * scale)))
        wave_pen.setColor(QColor(52, 211, 153, max(80, alpha)))
        painter.setPen(wave_pen)
        painter.drawLine(
            QPointF(cx + offset_x, cy - bar_h / 2),
            QPointF(cx + offset_x, cy + bar_h / 2),
        )

    # 4. Monospace "AI" or recording indicator dot at top right
    dot_cx = size - 36.0 * scale
    dot_cy = 36.0 * scale
    dot_radius = 7.0 * scale

    # Outer glow dot
    dot_glow = QRadialGradient(dot_cx, dot_cy, dot_radius * 2)
    dot_glow.setColorAt(0.0, QColor(16, 185, 129, 200))
    dot_glow.setColorAt(1.0, QColor(16, 185, 129, 0))
    painter.setPen(Qt.NoPen)
    painter.setBrush(dot_glow)
    painter.drawEllipse(QPointF(dot_cx, dot_cy), dot_radius * 2, dot_radius * 2)

    # Solid indicator dot
    painter.setBrush(QColor("#10b981"))
    painter.drawEllipse(QPointF(dot_cx, dot_cy), dot_radius, dot_radius)

    painter.end()
    return image


def save_multi_res_ico(ico_path: Path):
    """Saves a proper Windows multi-resolution ICO file with 16, 24, 32, 48, 64, 128, and 256px frames."""
    import struct
    from PySide6.QtCore import QBuffer, QIODevice

    sizes = [16, 24, 32, 48, 64, 128, 256]
    images_data = []

    for s in sizes:
        img = generate_icon(s)
        buf = QBuffer()
        buf.open(QIODevice.WriteOnly)
        img.save(buf, "PNG")
        images_data.append((s, bytes(buf.data())))

    # ICO Header: Reserved (0), Type (1 = Icon), Count
    header = struct.pack("<HHH", 0, 1, len(images_data))
    offset = 6 + len(images_data) * 16

    entries = []
    for s, data in images_data:
        w = 0 if s == 256 else s
        h = 0 if s == 256 else s
        entry = struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(data), offset)
        entries.append(entry)
        offset += len(data)

    ico_bytes = header + b"".join(entries) + b"".join(d for _, d in images_data)
    with open(ico_path, "wb") as f:
        f.write(ico_bytes)


def main():
    app = QApplication(sys.argv)
    assets_dir = Path(__file__).resolve().parent
    assets_dir.mkdir(parents=True, exist_ok=True)

    png_path = assets_dir / "icon.png"
    ico_path = assets_dir / "icon.ico"

    img_256 = generate_icon(256)
    img_256.save(str(png_path), "PNG")
    print(f"Saved PNG icon: {png_path}")

    # Save multi-resolution ICO
    save_multi_res_ico(ico_path)
    print(f"Saved Multi-resolution ICO icon: {ico_path}")


if __name__ == "__main__":
    main()
