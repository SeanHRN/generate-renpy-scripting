from krita import *
import sys
import math
from os.path import join, exists
import webbrowser
from PyQt5.QtWidgets import *
KI = Krita.instance()
default_outfile_name = "rpblock.txt"
indent = 4
decimal_place_count = 3

def parseValuesIntoList(name, sub_to_check):
    list = []
    if name.lower().find(sub_to_check) != -1:
        properties = name.lower()[name.lower().find(" " + sub_to_check):]
        if properties.find("=") != -1:
            properties = properties[properties.find("=")+1:]
        stopper = len(properties)
        for element in range (0, len(properties)):
            if properties[element].isalpha():
                stopper = element
                break
        properties = properties[:stopper]
        properties = properties.replace(" ","")
        list = [float(n) for n in properties.split(",")]
    return list

def parseLayers(layer, layer_name_list, coordinates_list, centers_list):
    if layer.visible() == True:
        layer_name_sublist = []
        coordinates_sublist = []
        centers_sublist = []
        lower_n = layer.name().lower()
        if lower_n.find(" e=") != -1:
            layer_name_list.append(layer.name())
            coord_x, coord_y, center_point = 0, 0, [0,0]
            if lower_n.find(" t=false") == -1 and lower_n.find(" t=no") == -1:
                coord_x = layer.bounds().topLeft().x()
                coord_y = layer.bounds().topLeft().y()
                center_point = layer.bounds().center()
            coordinates_list.append([coord_x, coord_y])
            centers_list.append([center_point.x(), center_point.y()])
        elif layer.type() == "grouplayer":
            for child in layer.childNodes():
                parseLayers(child, layer_name_sublist, coordinates_sublist, \
centers_sublist)
        layer_name_list.extend(layer_name_sublist)
        coordinates_list.extend(coordinates_sublist)
        centers_list.extend(centers_sublist)

def closestNum(num_list, value):
    return num_list[min(range(len(num_list)), key = lambda i: abs(num_list[i]-value))]

def truncate(number, digit_count):
    step = 10.0 ** digit_count
    return math.trunc(step * number) / step

def generateSpaces(spacing_count):
    step = 1.0 / (spacing_count - 1)
    spacing_list = []
    for i in range(spacing_count):
        spacing_list.append(truncate(i*step, decimal_place_count))
    return spacing_list

def calculateAlign(data_list, centers_list, spacing_count):
    """
    calculateAlign converts the pos(x,y) coordinates
    in the data list into align(x,y) coordinates
    by comparing the center point of each image
    to a finite set of values from 0.0 to 1.0.
    """
    width, height = 1, 1
    currentDoc = KI.activeDocument()
    if currentDoc != None:
        width = currentDoc.width()
        height = currentDoc.height()

    spacing_list = generateSpaces(spacing_count)
    new_data_list = []
    for d, c in zip(data_list, centers_list):
        xalign = closestNum(spacing_list, (c[0] / width))
        yalign = closestNum(spacing_list, (c[1] / height))
        new_data_list.append(tuple((d[0],xalign,yalign)))
    return new_data_list

def getData(button_num, spacing_count):
    file_open = False
    data_list = []
    layer_names = []
    all_coords = []
    all_centers = []
    currentDoc = KI.activeDocument()
    if currentDoc != None:
        file_open = True
        root_node = currentDoc.rootNode()
        for i in root_node.childNodes():
            parseLayers(i, layer_names, all_coords, all_centers)

    for name, coord_indv in zip(layer_names, all_coords):
        if name.lower().find(" e=") != -1:
            margin_list = parseValuesIntoList(name, "m=")
            if margin_list:
                coord_indv[0] -= max(margin_list)
                coord_indv[1] -= max(margin_list)
            size_list = parseValuesIntoList(name, "s=")
            if size_list:
                coord_indv[0] = round(coord_indv[0] * (min(size_list)/100))
                coord_indv[1] = round(coord_indv[1] * (min(size_list)/100))
            name = name[0:name.lower().find(" e=")]
            data_list.append(tuple((name, coord_indv[0], coord_indv[1])))

    if button_num == 2:
        data_list = calculateAlign(data_list, all_centers, spacing_count)
    return file_open, data_list


def writeData(input_data, path, format_num):
    outfile = open(path, "w")
    outfile.write("\n")
    prefix = "pos"
    if format_num == 2:
        prefix = "align"
    for d in input_data:
        outfile.write(f"{' ' * indent}show {d[0]}:\n")
        outfile.write(f"{' ' * (indent * 2)}{prefix} ({str(d[1])}, {str(d[2])})\n")
    outfile.write("\n")
    outfile.write(f"{' ' * indent}pause")
    outfile.close()


class GenerateRenpyScripting(DockWidget):
    title = "Generate Ren'Py Scripting"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.title)
        self.createInterface()

    def createInterface(self):

        export_label = QLabel("Export")
        export_label.setToolTip("Export a file with a block of Ren'Py scripting\
for a quick copy and paste.")

        pos_button = QPushButton("pos(x, y)")
        pos_button.clicked.connect(lambda: self.process(1))

        align_button = QPushButton("align(x, y)")
        align_button.clicked.connect(lambda: self.process(2))

        self.spacing_slider = QSlider(Qt.Horizontal, self)
        self.spacing_slider.setGeometry(30, 40, 200, 30)
        self.spacing_slider.setRange(2, 9)
        self.spacing_slider.setValue(9)
        self.spacing_slider.setFocusPolicy(Qt.NoFocus)
        self.spacing_slider.setPageStep(1)
        self.spacing_slider.setTickInterval(1)
        self.spacing_slider.setTickPosition(QSlider.TicksBelow)
        self.spacing_slider.valueChanged[int].connect(self.updateSpacingValue)
        self.spacing_text = QLabel("align(x,y) Spacing Count: ")
        self.spacing_text.setToolTip("Choose number of evenly-distributed \
spaces to use for align(x, y).")
        self.spacing_number_label = QLabel(f"{self.spacing_slider.value()}")
        self.spacing_number_label.setAlignment(Qt.AlignVCenter)
        self.rule_of_thirds_check = QCheckBox("Rule of Thirds")
        self.rule_of_thirds_check.setToolTip("Set align(x, y) \
statements to Rule of Thirds intersections. This is equivalent to using 4 spaces.")
        self.rule_of_thirds_check.setChecked(False)

        scale_label = QLabel("Scale Percentage Size Calculator")
        self.scale_box_percent = QSpinBox(self)
        self.scale_box_percent.setRange(0, 100)
        self.scale_box_percent.setValue(100)
        self.scale_box_percent.valueChanged[int].connect(self.updateScaleCalculation)
        self.scale_text = QLabel("% scale dimensions:", self)
        self.scale_w_h_text = QLabel(f"0 x 0 px", self)
        self.scale_w_h_text.setToolTip("This is how big the composite image \
would be at that percentage scale.")

        filename_label = QLabel("Output File")
        self.filename_line = QLineEdit()
        self.filename_line.setToolTip("Output file name with .[extension]")
        self.filename_line.setText(default_outfile_name)

        main_layout = QVBoxLayout()
        export_layout = QVBoxLayout()
        spacing_layout = QHBoxLayout()
        scale_layout = QHBoxLayout()

        export_layout.addWidget(export_label)
        export_layout.addWidget(pos_button)
        export_layout.addWidget(align_button)
        main_layout.addLayout(export_layout)

        spacing_layout.setContentsMargins(0,0,0,0)
        spacing_layout.addWidget(self.spacing_text)
        spacing_layout.addWidget(self.spacing_number_label)
        spacing_layout.addWidget(self.spacing_slider)
        spacing_layout.addWidget(self.rule_of_thirds_check)
        main_layout.addLayout(spacing_layout)

        main_layout.addWidget(scale_label)
        scale_layout.addWidget(self.scale_box_percent)
        scale_layout.addWidget(self.scale_text)
        scale_layout.addWidget(self.scale_w_h_text)
        main_layout.addLayout(scale_layout)

        main_layout.addWidget(filename_label)
        main_layout.addWidget(self.filename_line)
        main_layout.addStretch()

        mainWidget = QWidget(self)
        mainWidget.setLayout(main_layout)
        self.setWidget(mainWidget)

    def updateScaleCalculation(self):
        multiplier = self.scale_box_percent.value() / 100
        currentDoc = KI.activeDocument()
        width, height = 0, 0
        if currentDoc != None:
            width = round(currentDoc.width() * multiplier)
            height = round(currentDoc.height() * multiplier)
        self.scale_w_h_text.setText(f"{width} x {height} px")

    def updateSpacingValue(self):
        self.spacing_number_label.setText(str(self.spacing_slider.value()))

    def process(self, button_num):
        spacing_count = 9 # Just a placeholder value that works.
        if self.rule_of_thirds_check.isChecked():
            spacing_count = 4
        else:
            spacing_count = self.spacing_slider.value()
        file_open_test_result, data = getData(button_num, spacing_count)
        push_message = ""
        path = ""
        if file_open_test_result == True:
            path = str(QFileDialog.getExistingDirectory(None, "Select a save location."))
            outfile_name = default_outfile_name
            if self.filename_line.text() != "":
                outfile_name = self.filename_line.text()
            path += "/" + outfile_name
            writeData(data, path, button_num)
            outfile_exists = exists(path)
            if outfile_exists:
                webbrowser.open(path)
            else:
                push_message = "Failure: Open a Krita document."
                QMessageBox.information(QWidget(), "Generate Ren'Py Scripting", push_message)

    def canvasChanged(self, canvas):
        pass

def registerDocker():
    Krita.instance().addDockWidgetFactory(DockWidgetFactory\
("generateRenpyScripting", DockWidgetFactoryBase.DockRight\
 , GenerateRenpyScripting))
