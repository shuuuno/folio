"""24px 격자 위에 같은 선 두께로 그린 UI 아이콘."""
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor, QPainterPath


def icon(name, color="#566176"):
    result = QIcon()
    for mode, state, ink in ((QIcon.Mode.Normal, QIcon.State.Off, color),
                             (QIcon.Mode.Normal, QIcon.State.On, "#4361DE"),
                             (QIcon.Mode.Active, QIcon.State.Off, color),
                             (QIcon.Mode.Disabled, QIcon.State.Off, "#ADB5C2"),
                             (QIcon.Mode.Disabled, QIcon.State.On, "#ADB5C2")):
        for size in (16, 20, 24, 32):
            pix = QPixmap(size * 2, size * 2)
            pix.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pix)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.scale(size * 2 / 24, size * 2 / 24)
            painter.setPen(QPen(QColor(ink), 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            def line(*p): painter.drawLine(QPointF(*p[:2]), QPointF(*p[2:]))
            def path(points, closed=False):
                shape = QPainterPath(QPointF(*points[0]))
                for point in points[1:]: shape.lineTo(QPointF(*point))
                if closed: shape.closeSubpath()
                painter.drawPath(shape)
            if name == "file":
                path([(6,3),(14,3),(19,8),(19,21),(5,21),(5,3),(6,3)])
                path([(14,3),(14,8),(19,8)])
                line(8,12,15,12); line(8,16,13,16)
            elif name == "folder":
                path([(3,8),(3,5),(9,5),(11,8),(21,8),(19,19),(3,19),(3,8),(21,8)])
            elif name == "save":
                path([(4,3),(17,3),(21,7),(21,21),(3,21),(3,3),(4,3)])
                path([(7,3),(7,9),(16,9),(16,3)])
                path([(7,21),(7,14),(17,14),(17,21)])
            elif name == "cursor":
                path([(5,3),(18,13),(12,14),(9,20),(5,3)], True)
            elif name == "edit":
                path([(5,17),(15,4),(20,8),(10,21),(5,21),(5,17)])
                line(13,7,18,11)
            elif name == "text":
                path([(4,7),(4,4),(18,4),(18,7)]); line(11,4,11,20); line(7,20,15,20)
                line(20,14,20,20); line(17,17,23,17)
            elif name == "sign":
                shape = QPainterPath(QPointF(3,17))
                shape.cubicTo(7,11,15,0,12,4); shape.cubicTo(4,15,7,23,12,15)
                shape.cubicTo(14,10,14,19,17,15); shape.cubicTo(19,12,18,18,22,15)
                painter.drawPath(shape); line(3,22,21,22)
            elif name == "layers":
                path([(3,8),(12,3),(21,8),(12,13),(3,8)]); path([(3,13),(12,18),(21,13)]); path([(3,18),(12,23),(21,18)])
            elif name in ("undo", "redo"):
                if name == "redo": painter.translate(24,0); painter.scale(-1,1)
                path([(8,4),(3,9),(8,14)]); shape=QPainterPath(QPointF(3,9)); shape.lineTo(14,9); shape.cubicTo(23,9,23,20,14,20); painter.drawPath(shape)
            elif name == "search":
                painter.drawEllipse(QRectF(3,3,12,12)); line(14,14,21,21)
            elif name == "sidebar":
                painter.drawRoundedRect(QRectF(3,4,18,16),2,2); line(9,4,9,20)
            elif name in ("plus", "minus"):
                line(5,12,19,12)
                if name == "plus": line(12,5,12,19)
            elif name in ("left", "right", "down"):
                if name == "right": painter.translate(24,0); painter.scale(-1,1)
                if name == "down": painter.translate(0,24); painter.rotate(-90)
                path([(14,6),(8,12),(14,18)])
            elif name == "close":
                line(7,7,17,17); line(17,7,7,17)
            elif name == "fit":
                line(3,5,3,19); line(21,5,21,19); line(6,12,18,12)
                path([(9,9),(6,12),(9,15)]); path([(15,9),(18,12),(15,15)])
            elif name == "convert":
                path([(3,7),(20,7),(16,3)]); path([(21,17),(4,17),(8,21)])
            elif name == "history":
                painter.drawArc(QRectF(4,4,16,16),30*16,300*16)
                path([(2,4),(2,9),(7,9)]); path([(12,7),(12,12),(16,14)])
            elif name == "more":
                painter.setBrush(QColor(ink)); painter.setPen(Qt.PenStyle.NoPen)
                for x in (5,12,19): painter.drawEllipse(QPointF(x,12),1.5,1.5)
            elif name == "check":
                path([(5,12),(10,17),(20,6)])
            painter.end()
            pix.setDevicePixelRatio(2)
            result.addPixmap(pix, mode, state)
    return result
