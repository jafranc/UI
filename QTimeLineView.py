from PyQt5.QtCore import QPersistentModelIndex, QPoint, QRect, QEvent, QModelIndex, Qt
from PyQt5.QtGui import QHoverEvent, QHelpEvent, QPainter, QPalette, QPen, QColor, QColorConstants
from PyQt5.QtWidgets import (QListView,
                             QAbstractItemView,
                             QTableView,
                             QTreeView, QStyleOptionViewItem, QStyle, QAbstractScrollArea)

import QTimeLineItemDelegate

class QTimeLineView(QAbstractItemView):
    hoverIndex: QPersistentModelIndex
    scrollOffset: QPoint

    scale: float = 1.
    timestempSectionHeight: int = 30
    timestampPer100Pixels: int = 1.0
    layerHeight: int = 20

    def __init__(self):

        super().__init__()

        self.viewport().setAttribute(Qt.WA_Hover)
        self.setItemDelegate(QTimeLineItemDelegate())
        self.horizontalScrollBar().setSingleStep(10)
        self.horizontalScrollBar().setPageStep(100)
        self.verticalScrollBar().setSingleStep(self.layerHeight)
        self.verticalScrollBar().setPageStep(self.layerHeight * 5)
        self.viewport().setMinimumHeight(self.layerHeight + self.timestempSectionHeight)

    def setScale(self, val: float):
        self.scale = val
        self.updateScrollBars()
        self.viewport().update()

    def paintEvent(self, a0):
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.Antialiasing, True)

        timestempsRectIntersection = a0.rect() & QRect(0,0, a0.rect().width(), self.timestempSectionHeight)
        if not timestempsRectIntersection.isEmpty():
            painter.setBrush(self.palette().color(QPalette.Window).lighter(130))
            painter.setPen(QColorConstants.Black)

            painter.fillRect(timestempsRectIntersection, painter.brush())
            painter.drawLine(0, self.timestempSectionHeight, a0.rect().width(), self.timestempSectionHeight)

            painter.setPen(QPen(self.palette().color(QPalette.WindowText),1))
            for i in range(int(self.scrollOffset.x()/100 + 1)*100, a0.rect().width()+ self.scrollOffset.x() ,100):
                text = '{}s'.format(self.pixelsToDuration(i).count() * 1e6)
                textRect = painter.fontMetrics().boundingRect(text)

                textRect.translate(-self.scrollOffset.x(),0)
                text.translate( i - textRect.width()/2, self.timestempSectionHeight - 13)
                if textRect.right() > a0.rect().width() -5 :
                    textRect.translate(a0.rect().width() - textRect.right() -5 ,0)
                elif textRect.left():
                    textRect.translate(textRect.left()+5,0)

                painter.drawLine(i - self.scrollOffset.x(),
                                 self.timestempSectionHeight - 10,
                                 i- self.scrollOffset.x(),
                                 self.timestempSectionHeight)
                painter.drawText(textRect, text)

            option = QStyleOptionViewItem()
            for i in range(self.model().rowCount()):
                horizontalSeparatorLineY = i * self.layerHeight + self.timestempSectionHeight - self.scrollOffset.y() + self.layerHeight

                if horizontalSeparatorLineY < self.timestempSectionHeight:
                    continue
                if horizontalSeparatorLineY > self.viewport().height() + self.layerHeight:
                    break

                item = self.model().index(i,0)
                bgPenColor = item.data(Qt.DecorationRole).value
                bgFillColor = ...
                rectWithoutTimeStamps = a0.rect()
                rectWithoutTimeStamps.setTop(self.timestempSectionHeight)
                painter.setPen(bgPenColor)
                painter.fillRect(QRect(0, i*self.layerHeight + self.timestempSectionHeight - self.scrollOffset.y(),
                                       rectWithoutTimeStamps.width(), self.layerHeight) & rectWithoutTimeStamps, bgFillColor)
                painter.drawLine(0, horizontalSeparatorLineY, rectWithoutTimeStamps.width(), horizontalSeparatorLineY)
                for j in range(self.model().columnCount()):
                    segment = self.model().index(i,j)
                    if not segment.isValid():
                        continue
                    option.rect = self.visualRect(segment)
                    # ???
                    if segment == self.hoverIndex:
                        option.state.State_MouseOver

                    if option.rect.intersects(rectWithoutTimeStamps):
                        option.rect = option.rect & rectWithoutTimeStamps
                        self.itemDelegate().paint(painter,option,segment)
            for i in range( int((a0.rect().left() - self.scrollOffset.x()) /100 + 1) * 100,
                            a0.rect().right() + self.scrollOffset.x(), 100):
                painter.setPen(QColor(0,0,0,50))
                painter.drawLine(i - self.scrollOffset.x(),
                                 self.timestempSectionHeight if (self.timestempSectionHeight > a0.rect().top()) else a0.rect().top(),
                                 i - self.scrollOffset.x(),
                                 a0.rect().bottom())


    def resizeEvent(self, e):
        self.updateScrollBars()
        QAbstractItemView.resizeEvent(e)

    def showEvent(self, a0):
        self.updateScrollBars()
        QAbstractItemView.showEvent(a0)

    def indexAt(self, p):
        row = (p.y() - self.timestempSectionHeight) / self.layerHeight
        for i in range(self.model().columnCount()):
            if self.visualRect(self.model().index(row,i)).contains(p):
                return self.model().index(row,i)
        return

    def scrollTo(self, index, hint=None):
        return

    def visualRect(self, index):
        return self.itemRect(index).translated(- self.scrollOffset)

    def horizontalOffset(self):
        return 0

    def isIndexHidden(self, index):
        return False

    def moveCursor(self, cursorAction, modifiers):
        return

    def setSelection(self, rect, command):
        return

    def verticalOffset(self):
        return 0

    def visualRegionForSelection(self, selection):
        return

    def viewportEvent(self, e : QHoverEvent):
        if e.type() in [QEvent.HoverMode, QEvent.HoverEnter]:
            self.update(self.hoverIndex)
            self.hoverIndex = self.indexAt(e.pos())
            if self.hoverIndex.isValid():
                self.hoverIndex = self.indexAt(e.pos())
                self.update(self.hoverIndex)
        elif e.type() in [QEvent.HoverLeave]:
            self.update(self.hoverIndex)
            self.hoverIndex = QModelIndex()
            self.update(self.hoverIndex)
        elif e.type() in [QEvent.ToolTip, QEvent.QueryWhatsThis, QEvent.WhatsThis]:
            he = QHelpEvent(e)
            index = self.indexAt(he.pos())
            option = QStyleOptionViewItem()
            option.rect = self.visualRect(index).translated(-self.scrollOffset.x(), -self.scrollOffset.y())
            option.state |= QStyle.State_HasFocus if ( index == self.currentIndex() ) else QStyle.State_None

            delegate = self.itemDelegateForIndex(index)
            if not delegate:
                return False
            return delegate.helpEvent(he,self,option,index)

        return QAbstractScrollArea.viewportEvent(e)

    # QAbstactScrollArea
    def scrollContentsBy(self, dx, dy):
        self.scrollOffset -= QPoint(dx,dy)
        QAbstractItemView.scrollContentsBy(dx,dy)

    def itemRect(self, index):
        startTime = index.data( Qt.UserRole + 1).toDouble()
        duration = index.data(Qt.UserRole + 2).toDouble()
        x = self.durationToPixels(startTime)
        width = self.durationToPixels(duration)
        return QRect(x, index.row()* self.layerHeight + self.timestempSectionHeight, self.width(), self.layerHeight )

    def updateScrollBars(self):
        if self.model() is None:
            return
        max_ = 0
        for i in range(self.model().rowCount()):
            item = self.model().index(i, self.model().columnCount() - 1)
            if not item.isValid():
                continue
            max_ = max(self.itemRect(item) - self.viewport().width())

        self.horizontalScrollBar().setRange(0, max_)
        self.verticalScrollBar().setRange(0,
                                          self.model().rowCount() * self.layerHeight + self.timestempSectionHeight - self.viewport().height())

    def durationToPixels(self, val):
        return val * self.scale * 1000

    def pixelsToDuration(self, val):
        return val / self.scale / 1000
