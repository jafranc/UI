# from PyQt5.QtGui import QGuiApplication
# from PyQt5.QtQml import QQmlApplicationEngine
import re
from functools import partial

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
                             QSlider, QTreeWidget, QGridLayout)

from PyQt5 import QtQuick
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

        self.labellist = {}
        self.setWindowTitle("My App")
        self.itree = ET.parse('test.xml')
        # self.itree = ET.parse('deadoil_3ph_corey_1d.xml')
        self.otree = ET.ElementTree()
        nb_elt = len(self.itree.getroot().findall(".//*"))

        self.qc_time_list = ['sec', 'hours', 'days', 'years']
        self.qc_time_combos = {}

        self.vlayout = QGridLayout()
        self.treewidget = QTreeWidget()
        self.treewidget.clicked.connect(self.activate_button)
        self.vlayout.addWidget(self.treewidget, 0, 0)

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
        while len(visit):
            child = visit.pop(0)
            childit = visit_item.pop(0)
            # col = ((col+1) if gen==old_gen else col) % 3
            gen = gen_num.pop(0)
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
            frame.setLineWidth(2)
            frame.setFrameStyle(QFrame.Panel | QFrame.Plain)
            layout = QFormLayout()
            layout.addRow(QLabel(suffix + child.tag))

            childit.setText(0, child.tag)
            print(gen, child.tag)

            for k, v in child.attrib.items():
                if re.match(r'logLevel', k):
                    qc = QComboBox()
                    qc.addItems([str(i) for i in range(0, 8)])
                    layout.addRow(k, qc)
                elif re.match(r'newton?', k):
                    ql = QHBoxLayout()
                    qe = QLineEdit(v)
                    ql.addWidget(qe)
                    qc = QComboBox()
                    qc.addItems(self.qc_time_list)
                    self.qc_time_combos[k] = (qc, [qc.currentIndex(), -1])
                    qc.currentIndexChanged.connect(partial(self.on_currentIndexChanged, k, qe))
                    ql.addWidget(qc)
                    layout.addRow(k, ql)
                elif re.match(r'useMass|directParallel', k):
                    qcb = QCheckBox()
                    qcb.setChecked(bool(int(v)))
                    layout.addRow(k, qcb)
                else:
                    layout.addRow(k, QLineEdit(v))

            frame.setLayout(layout)

            if self.vlayout.itemAtPosition(gen+1,col+1) is None :
                self.vlayout.addWidget(frame, gen + 1, col + 1)
            else:
                self.vlayout.addWidget(frame, gen + 2, col + 1)


        self.button = QPushButton("Save as...")
        self.button.clicked.connect(self.file_save)

        self.button.hide()

        self.vlayout.addWidget(self.button)
        container = QWidget()
        container.setLayout(self.vlayout)
        self.setCentralWidget(container)

    def activate_button(self):
        self.button.show()

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
