import re
from functools import partial

from dateutils import date
import numpy as np
import vtk
from vtkmodules.util import numpy_support
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QColorConstants, QColor
from PyQt5.QtWidgets import (QApplication,
                             QMainWindow,
                             QLabel,
                             QLineEdit,
                             QMenu,
                             QAction,
                             QScrollArea,
                             QVBoxLayout,
                             QHBoxLayout,
                             QWidget,
                             QFormLayout,
                             QFrame,
                             QFileDialog,
                             QComboBox,
                             QCheckBox,
                             QTreeWidgetItem,
                             QTreeWidget, QGridLayout, QAbstractItemView, QDialog, QListWidget,
                             QDialogButtonBox, QPushButton)

from PyQt5 import QtCore
import xmlschema
import xml.etree.ElementTree as ET
import sys

from QTimeLineView import QTimeLineView
from xml_formatter import format_file


class PopUpWindows(QDialog):
    def __init__(self):
        super().__init__()

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)

        buttons = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.button_box = QDialogButtonBox(buttons)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.list_widget)
        self.layout.addWidget(self.button_box)

        self.setLayout(self.layout)

    def setFields(self, field_list):
        [self.list_widget.addItem(field) for field in field_list]

    def selected(self):
        return [item.text() for item in self.list_widget.selectedItems()]

    def closeEvent(self, event):
        event.accept()


class VTKPopUpWindows(QWidget):

    def __init__(self, elt: ET.ElementTree):
        super().__init__()
        self.txtActor = None
        self.actor = None
        layout = QGridLayout()
        self.mesh = None

        # main widget
        self.fname = elt.get('file')
        self.elt = elt  # tmp
        self.setLayout(layout)
        self.meshfields = {}
        self._setVTKenv_(0, 0)

        # menu-action widget
        fieldCombo = QComboBox()
        cmpCombo = QComboBox()
        for field, num_field in self.meshfields.items():
            fieldCombo.addItem(field)
        fieldCombo.currentIndexChanged.connect(partial(self.update_cmp_combo, layout))
        layout.addWidget(fieldCombo, 0, 0, 1, 2)

        snapshotBt = QPushButton("Snapshot")
        snapshotBt.clicked.connect(partial(self.on_snapButtonClicked, self.vtkWidget.GetRenderWindow()))
        layout.addWidget(snapshotBt, 0, 3, 1, 1)

    def update_cmp_combo(self, layout, ix_field: int):
        currentField = self.mesh.GetCellData().GetArray(ix_field)
        if currentField.GetNumberOfComponents() > 1:
            coupled_combo = QComboBox()
            coupled_combo.addItems([str(i) for i in range(currentField.GetNumberOfComponents())])
            coupled_combo.currentIndexChanged.connect(partial(self.update_cmp_component, ix_field))
            layout.addWidget(coupled_combo, 0, 2, 1, 1)
        else:
            self.renderField(ix_field,0)

    def update_cmp_component(self, field_index: int, ix_compo: int):
        self.renderField(field_index, ix_compo)

    def on_snapButtonClicked(self, ren: vtk.vtkRenderWindow):
        win_to_img = vtk.vtkWindowToImageFilter()
        win_to_img.SetInput(ren)
        win_to_img.SetScale(1)
        win_to_img.SetInputBufferTypeToRGB()
        writer = vtk.vtkPNGWriter()
        writer.SetFileName('Snap_' + str(date.today()) + '.png')
        writer.SetInputConnection(win_to_img.GetOutputPort())
        writer.Write()

    def _setVTKenv_(self, field_index, component):

        self.vtkWidget = QVTKRenderWindowInteractor(self)
        self.layout().addWidget(self.vtkWidget, 1, 0, 4, 4)

        self.ren = vtk.vtkRenderer()
        self.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()

        # Create source
        reader = vtk.vtkXMLUnstructuredGridReader()
        reader.SetFileName(self.fname)
        reader.Update()

        # source = vtk.vtkSphereSource()
        # source.SetCenter(0, 0, 0)
        # source.SetRadius(5.0)

        self.mesh = reader.GetOutput()
        self._loadFields_(self.elt, self.mesh)

        # lut
        lut = vtk.vtkLookupTable()
        lut.SetNumberOfColors(256)
        lut.SetHueRange(0.667, 0.)
        lut.Build()
        # lut.SetTableValue(0,1,0,0)
        # lut.SetTableValue(1,0.5,0.5,0)
        # lut.SetTableValue(2,0,1,0)

        # Create a mapper
        self.mapper = vtk.vtkDataSetMapper()
        self.mapper.SetInputData(self.mesh)
        self.mapper.SetLookupTable(lut)
        self.mapper.SetColorModeToMapScalars()
        self.mapper.ScalarVisibilityOn()
        self.mapper.SetScalarModeToUseCellFieldData()

        # Create an actor
        self.actor = vtk.vtkActor()
        self.actor.SetMapper(self.mapper)
        self.actor.GetProperty().SetEdgeVisibility(True)

        self.txtActor = vtk.vtkTextActor()

        self.renderField(field_index, component)

        self.ren.AddActor(self.actor)
        self.ren.AddActor(self.txtActor)

        self.ren.ResetCamera()

        self.show()
        self.iren.Initialize()

    def renderField(self, field_index: int, compo: int):
        self.mapper.SelectColorArray(field_index)
        self.mapper.ColorByArrayComponent(field_index, compo)
        r = self.mesh.GetCellData().GetArray(field_index).GetRange()
        self.mapper.SetScalarRange(r[0], r[1])

        # Info text
        arr = numpy_support.vtk_to_numpy(
            self.mesh.GetCellData().GetArray(field_index))

        if self.mesh.GetCellData().GetArray(field_index).GetNumberOfComponents() > 1:
            arr = arr[compo, :]

        self.txtActor.SetInput("Range [{:.5e}:{:.5e}] \n".format(r[0], r[1])
                               + "Avg {:.5e} \n".format(np.mean(arr))
                               + "Std {:.5e} \n".format(np.std(arr)))
        self.txtActor.SetPosition2(20, 20)
        self.txtActor.GetTextProperty().SetFontSize(16)
        self.txtActor.GetTextProperty().SetColor(vtk.vtkNamedColors().GetColor3d("Gold"))

        self.show()

    def _loadFields_(self, elt: ET.ElementTree, mesh: vtk.vtkUnstructuredGrid) -> vtk.vtkCellData:
        if elt.get('fieldsToImport'):
            self.names = elt.get('fieldsToImport')
            for i in range(mesh.GetCellData().GetNumberOfArrays()):
                self.meshfields[mesh.GetCellData().GetArray(i).GetName()] = i


class TimeLineWindows(QWidget):

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.label = QLabel("Timeline Window")
        layout.addWidget(self.label)
        self.setLayout(layout)

    def setOnCloseCallback(self, callback):
        self.onCloseCallback = callback

    def closeEvent(self, a0):
        super().closeEvent(a0)
        self.onCloseCallback()


class MainWindow(QMainWindow):

    def on_currentIndexChanged(self, k, qe: QLineEdit, ix):
        print("former index", self.qc_time_combos[k][1][0])
        print("currentIndex:", ix)
        self.qc_time_combos[k][1][1] = ix
        source = float(qe.text())
        converters = [1., 60 * 60., 60 * 60 * 24., 60 * 60 * 24 * 365.]
        target = source * converters[self.qc_time_combos[k][1][0]] / converters[self.qc_time_combos[k][1][1]]
        qe.setText(str("{:e}".format(target)))
        self.qc_time_combos[k][1][0] = ix
        self.qc_time_combos[k][1][1] = -1

    def __init__(self):
        super().__init__()

        # self.labellist = {}
        self.visited = {}
        self.showlist = []
        self.qwidgetlist = {}
        self.qtreeitemlist = {}
        self.tagHashMap = {}
        self.setWindowTitle("GEOS standard UI")
        self.fname = 'test-vtk.xml'

        self.evaluate_sctree()

        self.otree = ET.ElementTree()
        # nb_elt = len(self.itree.getroot().findall(".//*"))

        self.qc_time_list = ['sec', 'hours', 'days', 'years']
        self.qc_time_combos = {}

        # menu block
        self.file_menu = QMenu("File", self)
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.file_open)
        self.file_menu.addAction(open_action)
        save_action = QAction("Save as ...", self)
        save_action.triggered.connect(self.file_save)
        self.file_menu.addAction(save_action)
        reset_action = QAction("Reset to default", self)
        reset_action.triggered.connect(self.reset_to_default)
        self.file_menu.addAction(reset_action)

        self.menuBar().addMenu(self.file_menu)

        # input tree block
        # todo decide if itree should be kept or not
        self.itree = ET.parse(self.fname)
        self.evaluate_tree(self.itree)

    def evaluate_sctree(self):
        self.sc = xmlschema.XMLSchema('schema.xsd')
        self.sc_tree = ET.ElementTree()
        parent = ET.Element('Problem')
        parent = self.dict_to_etree(self.sc.to_dict(self.fname), parent)
        self.sc_tree._setroot(parent)

    def evaluate_tree(self, itree):

        self.vlayout = QGridLayout()
        self.treewidget = QTreeWidget()
        self.treewidget.setHeaderLabel('Object Tree')
        self.treewidget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.treewidget.itemActivated.connect(self.activate_button)

        visit_etree = [itree.getroot()]
        visit_indices = [visit_etree[0].tag + '_0']  # root always unique
        visit_qtitem = [QTreeWidgetItem(self.treewidget)]
        visit_qtitem[0].setText(0, visit_etree[0].tag)

        gen_num = [0]
        col_num = [0]
        max_gen = 0

        # todo refactor in BFS with callback
        while len(visit_etree):
            child = visit_etree.pop(0)
            refomated_tag = visit_indices.pop(0)
            childit = visit_qtitem.pop(0)

            # col = ((col+1) if gen==old_gen else col) % 3
            gen = gen_num.pop(0)
            max_gen = gen if gen > max_gen else max_gen

            col = col_num.pop(0)
            visit_etree += list(child)
            visit_indices += self.avoid_duplicates(list(child))
            visit_qtitem += [QTreeWidgetItem(childit) for i in range(len(list(child)))]

            gen_num += len(list(child)) * [gen + 1]
            if child.tag == "Problem":
                col_num += range(0, len(list(child)))
            else:
                col_num += len(list(child)) * [col]

            frame = QFrame()

            frame.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
            frame_action_red = QAction("Reduce", frame)
            frame_action_red.triggered.connect(partial(self.reduction, child, frame))
            frame.addAction(frame_action_red)
            frame_action_aug = QAction("Augmente", frame)
            frame_action_aug.triggered.connect(partial(self.augmentation, child, frame))
            frame.addAction(frame_action_aug)

            # add TimeLine via context menu
            if child.tag == "Events":
                frame_action_tl = QAction("Generate TimeLine", frame)
                frame_action_tl.triggered.connect(partial(self.timelinePopUp, child, frame))
                frame.addAction(frame_action_tl)
            if child.tag == "VTKMesh":
                frame_action_vtk = QAction("Genrate VTK mesh view", frame)
                frame_action_vtk.triggered.connect(partial(self.vtkPopUp, child, frame))
                frame.addAction(frame_action_vtk)

            h = self.append_in_dict(child, frame)

            frame.setLineWidth(2)
            frame.setFrameStyle(QFrame.Panel | QFrame.Plain)
            layout = QFormLayout()
            layout.addRow(QLabel(child.tag))

            childit.setText(0, refomated_tag)
            childit.setExpanded(True)
            self.showlist.append(h)
            self.qtreeitemlist[h] = childit

            # todo refactor in special item
            for k, v in child.attrib.items():
                if re.match(r'logLevel', k):
                    qc = QComboBox()
                    qc.addItems([str(i) for i in range(0, 8)])
                    qc.currentIndexChanged.connect(partial(self.update_combo, child, k))
                    layout.addRow(k, qc)
                elif re.match(r'(max|begin|end)Time$', k) or re.match(r'(force|initial)Dt', k) \
                        or re.match(r'timeFrequency', k):
                    ql = QHBoxLayout()
                    qe = QLineEdit(v)
                    qe.textChanged.connect(partial(self.update_line, child, k))
                    ql.addWidget(qe)
                    qc = QComboBox()
                    qc.addItems(self.qc_time_list)
                    self.qc_time_combos[k] = (qc, [qc.currentIndex(), -1])
                    qc.currentIndexChanged.connect(partial(self.on_currentIndexChanged, k, qe))
                    ql.addWidget(qc)
                    layout.addRow(k, ql)
                elif re.match(r'useMass|directParallel|targetExactTimestep', k):
                    qcb = QCheckBox()
                    qcb.setChecked(bool(int(v)))
                    qcb.stateChanged.connect(partial(self.update_bool, child, k))
                    layout.addRow(k, qcb)
                else:
                    qe = QLineEdit(v)
                    qe.textChanged.connect(partial(self.update_line, child, k))
                    layout.addRow(k, qe)

            frame.setLayout(layout)

            max_gen = self.test_if_widget_present(col, frame, gen, max_gen)

        self.vlayout.addWidget(self.treewidget, 0, 0, max_gen - 1, 1)
        # make use of the qtimelineview widget we baked
        # self.timeline = self.addTimeline(self.itree)
        # self.vlayout.addWidget(self.timeline, max_gen - 1, 1, 1, self.vlayout.columnCount() - 1)
        container = QWidget()
        container.setLayout(self.vlayout)
        scollable_area = QScrollArea()
        scollable_area.setWidget(container)
        scollable_area.show()
        self.setCentralWidget(scollable_area)

    def filterEvent(self, tree: ET.ElementTree):

        # event is a tuple of a starttime, duration followed by string-tag and rgb color for QTimeLineView to picked up
        event = []

        for events in tree.getroot().findall("Events"):
            maxTime = float(events.attrib["maxTime"])
            for children in events:
                if children.tag == "PeriodicEvent":
                    periodic = children
                    if 'timeFrequency' in [key for key, _ in periodic.items()]:
                        timerange = np.arange(0, maxTime, float(periodic.attrib["timeFrequency"]))
                        event.extend([(starttime, 1, periodic.attrib["name"], [1, 0, 0]) for starttime in timerange])
                    elif ('endTime' in [key for key, _ in periodic.items()]) or (
                            'beginTime' in [key for key, _ in periodic.items()]):
                        starttime = float(periodic.attrib["beginTime"]) if (
                                'beginTime' in [key for key, _ in periodic.items()]) else 0
                        endtime = float(periodic.attrib["endTime"]) if (
                                'endTime' in [key for key, _ in periodic.items()]) else maxTime
                        duration = endtime - starttime
                        event.extend([(starttime, duration, periodic.attrib["name"], [1, 0, 0])])
                #
                elif children.tag == "SoloEvent":
                    solo = children
                    if ('endTime' in [key for key, _ in solo.items()]) or (
                            'beginTime' in [key for key, _ in solo.items()]):
                        starttime = float(solo.attrib["beginTime"]) if (
                                'beginTime' in [key for key, _ in solo.items()]) else 0
                        endtime = float(solo.attrib["endTime"]) if (
                                'endTime' in [key for key, _ in solo.items()]) else maxTime
                        duration = endtime - starttime
                        event.extend([(starttime, duration, solo.attrib["name"], [0, 1, 0])])

        return event

    def addTimeline(self, tree):

        event = self.filterEvent(tree)

        # by hand
        timeline = QTimeLineView()

        timeline.setModel(QStandardItemModel(timeline))
        timeline.model().clear()
        timeline.setScale(1.0)

        for i, ev in enumerate(event):
            # 1 layer per event model
            layer = QStandardItem("event_{}".format(i))
            layer.setData(QColorConstants.White, Qt.DecorationRole)
            layer.setData("event_{}".format(i), Qt.ToolTipRole)
            timeline.model().appendRow(layer)
            section = QStandardItem("Periodic")
            section.setData(QColorConstants.Blue.lighter(100), Qt.DecorationRole)
            section.setData(ev[2], Qt.ToolTipRole)
            section.setData(ev[0], Qt.UserRole + 1)  # start
            section.setData(ev[1], Qt.UserRole + 2)  # duration

            timeline.model().setItem(layer.row(), 1, section)

        ## new layer

        # layer2 = QStandardItem("todo")
        # layer2.setData(QColorConstants.White, Qt.DecorationRole)
        # layer2.setData("layer-2", Qt.ToolTipRole)
        # timeline.model().appendRow(layer2)
        #
        # section = QStandardItem("SECTION-2")
        # section.setData(QColorConstants.Blue, Qt.DecorationRole)
        # section.setData("sec2_data", Qt.ToolTipRole)
        # section.setData(1.45e5, Qt.UserRole + 1)
        # section.setData(2.22e5, Qt.UserRole + 2)
        #
        # timeline.model().setItem(layer2.row(), 1, section)

        timeline.show()

        return timeline

    def update_line(self, elt, k, text):
        elt.attrib[k] = text

    def update_combo(self, elt, k, value):
        elt.attrib[k] = str(value)

    def update_bool(self, elt, k, state):
        # No tri state
        elt.attrib[k] = "0" if state == 0 else "1"

    # todo check if can get parent widget otherwise
    def reduction(self, etree_elt, widget):

        rm_list = []
        sctree_elt = self.sc_tree.find('.//' + etree_elt.tag)
        for k, v in sctree_elt.attrib.items():
            if k in etree_elt.attrib and v == etree_elt.attrib[k]:
                rm_list.append(k)
                # delete rows with that label in widget
                layout = widget.layout()
                for irow in reversed(range(1, layout.rowCount())):
                    if layout.itemAt(irow, QFormLayout.LabelRole).widget().text() == k:
                        layout.removeRow(irow)

        for k in rm_list:
            del etree_elt.attrib[k]

    def augmentation(self, etree_elt, widget):
        pop_list = []
        msg_box = PopUpWindows()
        msg_box.setWindowTitle('Attribute to add')
        sctree_elt = self.sc_tree.find('.//' + etree_elt.tag)
        for k, v in sctree_elt.attrib.items():
            if k not in etree_elt.attrib:
                # delete rows with that label in widget
                pop_list.append(k)

        msg_box.setFields(pop_list)
        msg_box.exec()
        add_list = msg_box.selected()

        layout = widget.layout()
        sc_list = sctree_elt.attrib
        for k in add_list:
            layout.addRow(k, QLineEdit(sc_list[k]))
            etree_elt.set(k, sc_list[k])

    def vtkPopUp(self, etree_elt, widget):
        self.vtkWidget = VTKPopUpWindows(etree_elt)

    def timelinePopUp(self, etree_elt, widget):
        self.timelineBox = TimeLineWindows()
        self.timelineBox.setWindowTitle("Timeline for Events")
        timeline = self.addTimeline(self.itree)

        def updateWidget(widget: QFrame, timeline: QTimeLineView, elt: ET.ElementTree):
            if timeline.model() is None:
                return
            for i in range(1, timeline.model().rowCount()):
                item = timeline.model().index(i, timeline.model().columnCount() - 1)
                if not item.isValid():
                    continue
                # data extraction
                name = item.data(Qt.ToolTipRole)
                beginTime = item.data(Qt.UserRole + 1)  # start time
                endTime = beginTime + item.data(Qt.UserRole + 2)
                for children in elt:
                    if ((name in [values for _, values in children.items()]) and
                            (('beginTime' in [k for k, _ in children.items()]) or 'endTime' in [k for k, _ in
                                                                                                children.items()])):
                        children.attrib['beginTime'] = "{:.4e}".format(beginTime)
                        children.attrib['endTime'] = "{:.4e}".format(endTime)
            self.evaluate_tree(self.itree)

        self.timelineBox.setOnCloseCallback(partial(updateWidget, widget, timeline, etree_elt))

        self.timelineBox.layout().addWidget(timeline)
        self.timelineBox.show()

    def avoid_duplicates(self, etree_list):
        tag_list = [elt.tag for elt in etree_list]
        uniq = [item + '_0' for item in tag_list if tag_list.count(item) == 1]
        dup = [item for item in tag_list if tag_list.count(item) > 1]
        for elt in set(dup):
            c = 0
            for i, item in enumerate(dup):
                if item == elt:
                    dup[i] = item + '_' + str(c)
                    c += 1

        uniq.extend(dup)
        return uniq

    def append_in_dict(self, child, frame, c=0):
        h = hash(child.tag + '_' + str(c))
        if h not in self.qwidgetlist:
            self.tagHashMap[h] = child.tag + '_' + str(c)
            self.qwidgetlist[h] = frame
        else:
            h = self.append_in_dict(child, frame, c + 1)
        return h

    def test_if_widget_present(self, col, frame, gen, max_gen):
        if self.vlayout.itemAtPosition(gen + 1, col + 1) is None:
            self.vlayout.addWidget(frame, gen + 1, col + 1)
        else:
            max_gen = self.test_if_widget_present(col, frame, gen + 1, max_gen + 1)
        return max_gen

    def clean_widgets(self):

        self.qwidgetlist.clear()
        self.tagHashMap.clear()
        self.showlist.clear()
        for ic in range(self.vlayout.count()):
            self.vlayout.itemAt(ic).widget().deleteLater()

    def dict_to_etree(self, mdict: dict, parent):

        for k, v in mdict.items():
            if isinstance(v, list):
                elt = ET.Element(k)
                # sub
                parent.append(self.dict_to_etree(v[0], elt))
            else:
                parent.set(k[1:], v)

        return parent

    def activate_button(self):
        # self.button.show()
        # print('before')
        print([self.tagHashMap[h] for h in self.showlist])
        # self.appendAllChildren(self.showlist)
        for h in self.showlist:
            self.qwidgetlist[h].hide()
        self.showlist = []
        self.showlist = [h for item in self.treewidget.selectedItems() for h, v in self.qtreeitemlist.items() if
                         v == item]
        # self.appendAllChildren(self.showlist)
        for h in self.showlist:
            self.qwidgetlist[h].show()

    # def appendAllChildren(self, list):
    #     # show all children too
    #     for w in list:
    #         sublist = [ w[1].child(ic) for ic in range(0, w[1].childCount())]
    #         self.appendAllChildren(sublist)
    #         list.extend(sublist)

    def file_save(self):
        name = QFileDialog.getSaveFileName(self, 'Save File')
        # text = self.textEdit.toPlainText()
        # text = \
        self.gen_txt(name[0])
        format_file(name[0])

    def file_open(self):
        self.fname, _ = QFileDialog.getOpenFileName(self, 'Open File')
        self.clean_widgets()
        itree = ET.parse(self.fname)
        self.evaluate_tree(itree)
        self.evaluate_sctree()

    def reset_to_default(self):
        self.clean_widgets()
        self.evaluate_tree(self.sc_tree)
        self.evaluate_sctree()

    def DFS(self, qr, parent):

        h = hash(qr.text(0))
        self.visited[h] = True
        current = self.qform_to_etree(self.qwidgetlist[h])
        if parent is not None:
            parent.append(current)

        print(qr.childCount())

        for ic in range(qr.childCount()):
            h = hash(qr.child(ic).text(0))
            if not h in self.visited:
                self.DFS(qr.child(ic), current)

        print(current)

        return current

    def gen_txt(self, fname):
        index = self.vlayout.count()
        qr = self.treewidget.topLevelItem(0)
        print(self.qwidgetlist)
        print(self.tagHashMap)
        problem = self.DFS(qr, None)

        otree = ET.ElementTree()
        otree._setroot(problem)

        otree.write(fname, xml_declaration="xml version=\"1.0\"")

    def qform_to_etree(self, qframe):
        qform = qframe.layout()
        c = qform.rowCount()
        for j in range(0, c):
            ql = qform.itemAt(j, QFormLayout.LabelRole)
            qw = qform.itemAt(j, QFormLayout.FieldRole)
            if ql is None:
                new_elem = ET.Element(qw.widget().text())
            else:
                if isinstance(qw.layout(), QHBoxLayout):
                    # print("here")
                    right = qw.layout().itemAt(0).widget().text()
                elif isinstance(qw.widget(), QLineEdit):
                    right = qw.widget().text()
                elif isinstance(qw.widget(), QCheckBox):
                    right = '1' if qw.widget().isChecked() else '0'
                elif isinstance(qw.widget(), QComboBox):
                    right = str(qw.widget().currentIndex())

                new_elem.set(ql.widget().text(), right)
        return new_elem


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    app.exec()
