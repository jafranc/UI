# from PyQt5.QtGui import QGuiApplication
# from PyQt5.QtQml import QQmlApplicationEngine
import re
from functools import partial
from pprint import pprint

from PyQt5.QtWidgets import (QApplication,
                             QMainWindow,
                             QLabel,
                             QLineEdit,
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
                             QSlider, QTreeWidget, QGridLayout, QAbstractItemView)

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
        self.showlist = []
        self.qwidgetlist = {}
        self.qtreeitemlist = {}
        self.tagHashMap = {}
        self.setWindowTitle("GEOS standard UI")
        self.sc = xmlschema.XMLSchema('schema.xsd')
        self.fname = 'test.xml'
        # self.sc_tree = self.sc.to_etree(self.fname)
        pprint( self.sc.to_etree(self.fname) )
        self.itree = ET.parse(self.fname)
        # self.itree = ET.parse('deadoil_3ph_corey_1d.xml')
        self.otree = ET.ElementTree()
        nb_elt = len(self.itree.getroot().findall(".//*"))

        self.qc_time_list = ['sec', 'hours', 'days', 'years']
        self.qc_time_combos = {}

        self.vlayout = QGridLayout()
        self.treewidget = QTreeWidget()
        self.treewidget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.treewidget.itemActivated.connect(self.activate_button)



        suffix = '\t'

        visit = [self.itree.getroot()]
        visit_item = [QTreeWidgetItem(self.treewidget)]
        visit_item[0].setText(0, visit[0].tag)
        # visit_item[0].setText(0,"Test")
        # seconditem = QTreeWidgetItem(visit_item[0])
        # seconditem.setText(0,"Subtest")

        # for child in self.itree.iter():
        gen_num = [0]
        col_num = [0]
        max_gen = 0
        while len(visit):
            child = visit.pop(0)
            childit = visit_item.pop(0)
            # col = ((col+1) if gen==old_gen else col) % 3
            gen = gen_num.pop(0)
            max_gen = gen if gen > max_gen else max_gen
            col = col_num.pop(0)
            visit += list(child)
            visit_item += [QTreeWidgetItem(childit) for i in range(len(list(child)))]
            gen_num += len(list(child)) * [gen + 1]
            if child.tag == "Problem":
                col_num += range(0, len(list(child)))
            else:
                col_num += len(list(child)) * [col]

            print(range(col, col + len(list(child))))

            frame = QFrame()
            h = self.append_in_dict(child, frame)

            frame.setLineWidth(2)
            frame.setFrameStyle(QFrame.Panel | QFrame.Plain)
            layout = QFormLayout()
            layout.addRow(QLabel(suffix + child.tag))

            childit.setText(0, child.tag)
            childit.setExpanded(True)
            self.showlist.append(h)
            self.qtreeitemlist[h] = childit
            print(gen, child.tag)

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

        self.button = QPushButton("Save as...")
        self.button.clicked.connect(self.file_save)

        # self.button.hide()

        self.vlayout.addWidget(self.treewidget, 0, 0, max_gen, 1)
        self.vlayout.addWidget(self.button, max_gen + 1, 0)
        container = QWidget()
        container.setLayout(self.vlayout)
        self.setCentralWidget(container)

    def append_in_dict(self, child, frame, c = 0):
        h = hash(child.tag + str(c))
        if not h in self.qwidgetlist:
            self.tagHashMap[h] = child.tag
            self.qwidgetlist[h] = frame
            print('c=',c)
        else:
            h = self.append_in_dict(child, frame, c+1 )
        return h

    def test_if_widget_present(self, col, frame, gen, max_gen):
        if self.vlayout.itemAtPosition(gen + 1, col + 1) is None:
            self.vlayout.addWidget(frame, gen + 1, col + 1)
        else:
            max_gen = self.test_if_widget_present(col, frame, gen + 1, max_gen + 1)
        return max_gen

    def activate_button(self):
        # self.button.show()
        print('before')
        print([ self.tagHashMap[h] for h in self.showlist])
        # self.appendAllChildren(self.showlist)
        for h in self.showlist:
            self.qwidgetlist[h].hide()
        self.showlist = []

        self.showlist = [ h for item in self.treewidget.selectedItems() for h,v in self.qtreeitemlist.items() if v==item ]
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

    def gen_txt(self, fname):
        index = self.vlayout.count()
        print(index)
        problem = None
        for i in range(0, index - 1):  # last widget is a button
            qform = self.vlayout.itemAt(i).widget().layout()
            c = qform.rowCount()
            for j in range(0, c):
                # ql = qform.itemAt(j,QFormLayout.LabelRole).widget()
                qw = qform.itemAt(j, QFormLayout.FieldRole)
                ql = qform.itemAt(j, QFormLayout.LabelRole)
                if ql is None:
                    if problem is None:
                        problem = ET.Element(qw.widget().text())
                    else:
                        last_elem = ET.Element(qw.widget().text())
                        problem.append(last_elem)
                else:
                    if isinstance(qw.layout(), QHBoxLayout):
                        print("here")
                        right = qw.layout().itemAt(0).widget().text()
                    elif isinstance(qw.widget(), QLineEdit):
                        right = qw.widget().text()
                    elif isinstance(qw.widget(), QCheckBox):
                        right = '1' if qw.widget().isChecked() else '0'
                    elif isinstance(qw.widget(), QComboBox):
                        right = str(qw.widget().currentIndex())

                    last_elem.set(ql.widget().text(), right)

        otree = ET.ElementTree()
        otree._setroot(problem)

        indent(otree)
        otree.write(fname, xml_declaration="xml version=\"1.0\"")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    app.exec()
