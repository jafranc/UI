# from PyQt5.QtGui import QGuiApplication
# from PyQt5.QtQml import QQmlApplicationEngine
import re
from functools import partial
from pprint import pprint

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
                             QPushButton,
                             QComboBox,
                             QCheckBox,
                             QTreeWidgetItem,
                             QTreeWidget, QGridLayout, QAbstractItemView)

from PyQt5 import QtQuick
import xmlschema
import xml.etree.ElementTree as ET
import sys


def iter_indent(elt: ET.Element):
    for child in elt:
        child.text += '\t'
        iter_indent(child)
        child.tail += '\t'
    elt.text += '\t'


def indent(tree: ET.ElementTree):
    # init indent
    for elt in tree.iter():
        elt.text = '\n'
        elt.tail = '\n\n'

    # dfs indent
    iter_indent(tree.getroot())

    # correct level0
    for elt in tree.getroot():
        elt.tail = elt.tail[:-1]


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
        self.fname = 'test.xml'

        self.evaluate_sctree()

        self.otree = ET.ElementTree()
        # nb_elt = len(self.itree.getroot().findall(".//*"))

        self.qc_time_list = ['sec', 'hours', 'days', 'years']
        self.qc_time_combos = {}

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
        ##
        itree = ET.parse(self.fname)
        self.evaluate_file(itree)

    def evaluate_sctree(self):
        self.sc = xmlschema.XMLSchema('schema.xsd')
        self.sc_tree = ET.ElementTree()
        parent = ET.Element('Problem')
        parent = self.dict_to_etree(self.sc.to_dict(self.fname), parent)
        self.sc_tree._setroot(parent)

    def evaluate_file(self, itree):

        # self.plus_button = QPushButton("+")

        self.vlayout = QGridLayout()
        self.treewidget = QTreeWidget()
        self.treewidget.setHeaderLabel('Object Tree')
        self.treewidget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.treewidget.itemActivated.connect(self.activate_button)

        visit_etree = [itree.getroot()]
        visit_indices = [visit_etree[0].tag + '_0']  # root always unique
        visit_qtitem = [QTreeWidgetItem(self.treewidget)]
        visit_qtitem[0].setText(0, visit_etree[0].tag)
        # visit_qtitem[0].setText(0,"Test")
        # seconditem = QTreeWidgetItem(visit_qtitem[0])
        # seconditem.setText(0,"Subtest")
        # for child in self.itree.iter():
        gen_num = [0]
        col_num = [0]
        max_gen = 0
        # todo refactor in BFS
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
                    layout.addRow(k, qc)
                elif re.match(r'(max|begin|end)Time$', k) or re.match(r'(force|initial)Dt', k) \
                        or re.match(r'timeFrequency', k):
                    ql = QHBoxLayout()
                    qe = QLineEdit(v)
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
                    layout.addRow(k, qcb)
                else:
                    layout.addRow(k, QLineEdit(v))

            frame.setLayout(layout)

            max_gen = self.test_if_widget_present(col, frame, gen, max_gen)
        self.vlayout.addWidget(self.treewidget, 0, 0, max_gen - 1, 1)
        # self.vlayout.addWidget(self.button_open, max_gen, 0)
        # self.vlayout.addWidget(self.button_save, max_gen + 1, 0)
        container = QWidget()
        container.setLayout(self.vlayout)
        scollable_area = QScrollArea()
        scollable_area.setWidget(container)
        scollable_area.show()
        self.setCentralWidget(scollable_area)

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
            # self.vlayout.addWidget(self.plus_button, gen + 2, col+1)
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

        for k,v in mdict.items():
            if isinstance(v,list):
                elt = ET.Element(k)
                #sub
                parent.append( self.dict_to_etree(v[0],elt) )
            else:
                parent.set(k[1:],v)

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
        # with open(name, 'w') as f:
        #     f.write(text)
        # f.close()

    def file_open(self):
        self.fname, _ = QFileDialog.getOpenFileName(self, 'Open File')
        self.clean_widgets()
        itree = ET.parse(self.fname)
        self.evaluate_file(itree)
        self.evaluate_sctree()

    def reset_to_default(self):
        self.clean_widgets()
        self.evaluate_file(self.sc_tree)

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

        indent(otree)
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
