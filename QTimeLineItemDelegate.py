from PyQt5.QtGui import  QPen, QBrush
from PyQt5.QtWidgets import QAbstractItemDelegate
from PyQt5.QtCore import Qt


class QTimeLineItemDelegate(QAbstractItemDelegate):

    def __init__(self):
        super().__init__()

    def paint(self, painter, option, index):
        painter.save()
        color = index.data(Qt.DecorationRole)

        thickness = 0.0
        pen = QPen(color.darker(300), thickness)
        brush = QBrush(color)
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawRect(option.rect)
        painter.drawText(option.rect, Qt.AlignCenter, index.data(Qt.ToolTipRole))
        painter.restore()

    def sizeHint(self, option, index):
        return option.rect.size()
