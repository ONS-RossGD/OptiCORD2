
from PyQt5.Qt import QSvgRenderer
from PyQt5.QtCore import QEvent, QModelIndex, QObject, QPoint, QRectF, QSettings, pyqtSignal
from PyQt5.QtGui import QFontMetrics, QPainter, QPixmap, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QAbstractItemView, QAction, QListView, QMenu, QStyleOptionViewItem, QStyledItemDelegate, QWidget


class VisualisationList(QListView):
    """ListWidget for loaded visualisations"""

    def __init__(self, parent: QWidget) -> None:
        super(QListView, self).__init__(parent)
        # ListView setup
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # event filter to add right click menu
        self.installEventFilter(self)
        # init the custom model
        self.custom_model = VisListModel(self)
        self.custom_model.setHorizontalHeaderLabels(['Visualisation'])
        self.setModel(self.custom_model)
        # init the custom deligate
        self.deligate = VisualisationDeligate(self)
        self.setItemDelegate(self.deligate)
        # update viewport when svg render frame changes
        self.deligate.loading.repaintNeeded.connect(
            self.viewport().update)

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        """Custom event filter to manage item right click event"""        
        if event.type() == QEvent.ContextMenu and source is self:
            item = self.custom_model.item(
                self.currentIndex().row(), 0)
            menu = QMenu()
            delete = QAction('Delete', menu)
            menu.addActions([delete])
            delete.triggered.connect(lambda: print(item.filepath))
            if menu.exec(event.globalPos()):
                return True
        return super().eventFilter(source, event)

    def add_file(self, file: str) -> None:
        """Add the file to the queue"""
        self.custom_model.appendRow(VisualisationFile(file))

class VisListModel(QStandardItemModel):
    """Custom model for VisualisationList Widget"""

    def __init__(self, parent: QWidget) -> None:
        super(QStandardItemModel, self).__init__(parent)


class VisualisationFile(QStandardItem):
    """Custom QListWidget item for Visualisation files"""
    QUEUED = 0
    LOADING = 1
    SUCCESS = 2
    FAILURE = 3
    state_changed = pyqtSignal(int)
    state: int

    def __init__(self, filepath: str) -> None:
        super(QStandardItem, self).__init__(filepath.split('/')[-1])
        self.filepath = filepath
        self.state = self.QUEUED

class VisualisationDeligate(QStyledItemDelegate):
    """Item deligate for setting progress icons"""
    loading: QSvgRenderer

    def __init__(self, parent: VisualisationList) -> None:
        """Init QStyledItemDelegate but parent must be of type
        VisualisationList"""
        super().__init__(parent=parent)
        self.list = parent
        # svg animation for loading/queued
        self.loading = QSvgRenderer('./ui/resources/'
            f'{QSettings().value("active_theme").folder}'
            '/loading.svg', parent)
        # svg icon for success
        self.success = QPixmap('./ui/resources/'
            f'{QSettings().value("active_theme").folder}'
            '/success.svg')
        # svg icon for failed
        self.failed = QPixmap('./ui/resources/'
            f'{QSettings().value("active_theme").folder}'
            '/failed.svg')

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, 
        index: QModelIndex) -> None:
        """Custom painting to put icons to the right"""
        super().paint(painter, option, index)
        # get the VisualisationFile object
        item = self.list.custom_model.item(index.row(), 0)
        # verify state is recognised
        if item.state not in [VisualisationFile.QUEUED, 
            VisualisationFile.LOADING, VisualisationFile.SUCCESS,
            VisualisationFile.FAILURE]:
            raise ValueError('VisualisationFile state not recognised.')
        option = option.__class__(option)
        # get bounding box of list items text
        font_metrics = QFontMetrics(option.font)
        rect = font_metrics.boundingRect(index.data())
        # if loading or queued render the loading animation
        if item.state in [VisualisationFile.QUEUED,
            VisualisationFile.LOADING]:
            bounds = QRectF(rect.right()+10, option.rect.top()+2,
            option.rect.height()-4, option.rect.height()-4)
            self.loading.render(painter, bounds)
        # otherwise just paint the success/failure icon
        else:
            if item.state == VisualisationFile.SUCCESS:
                pixmap = self.success
            if item.state == VisualisationFile.FAILURE:
                pixmap = self.failed
            painter.drawPixmap(QPoint(rect.right()+10,
                option.rect.top()+2), pixmap)