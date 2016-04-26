import json
from PyQt4 import QtGui
from Control_Panel_View import Control_Panel_View, Control_Panel_View_Name
from Control_Panel_Widgets import QLineEditClear
from Control_Panel_Settings_Widgets import SettingsWidget
from Control_Panel_XBee_Sender import Control_Panel_XBee_Sender
from ..settings import Settings
from ..zigbee.XBee_Packet import XBee_Packet

class Setting_Filter_Match(object):
    NONE = 0
    KEY = 1
    HELP = 2
    VALUE = 3

class Control_Panel_Settings_View(Control_Panel_View):
    def show(self):
        self._add_menu_bar()

        defaults = Settings.get_settings(Settings.DEFAULTS_FILE)
        self._components = [keys for keys, values in sorted(defaults.iteritems(),
                                                            key=lambda (k, v): v["name"])]

        self._containers = []
        self._widgets = [None for c in self._components]
        self._best_matches = {}

        self._listWidget = QtGui.QListWidget()
        self._listWidget.addItems([defaults[c]["name"] for c in self._components])
        self._listWidget.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Expanding)
        self._listWidget.setCurrentRow(0)

        self._stackedLayout = QtGui.QStackedLayout()

        for c in self._components:
            container = QtGui.QScrollArea()
            container.setWidgetResizable(True)
            self._stackedLayout.addWidget(container)
            self._containers.append(container)

        self._listWidget.currentRowChanged.connect(self._stackedLayout.setCurrentIndex)
        self._stackedLayout.currentChanged.connect(lambda i: self._current_changed(i))
        self._current_changed(self._stackedLayout.currentIndex())

        # Create the layout and add the widgets.
        hbox_stacks = QtGui.QHBoxLayout()
        hbox_stacks.addWidget(self._listWidget)
        hbox_stacks.addLayout(self._stackedLayout)

        filterInput = QLineEditClear()
        filterInput.setPlaceholderText("Search...")
        filterInput.textChanged.connect(lambda text: self._filter(text))
        filterInput.setFixedWidth(self._listWidget.sizeHint().width())
        filterInput.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Maximum)

        saveButton = QtGui.QPushButton("Save")
        saveButton.clicked.connect(self._save)

        hbox_buttons = QtGui.QHBoxLayout()
        hbox_buttons.addWidget(filterInput)
        hbox_buttons.addStretch(1)
        hbox_buttons.addWidget(saveButton)

        vbox = QtGui.QVBoxLayout(self._controller.central_widget)
        vbox.addLayout(hbox_stacks)
        vbox.addLayout(hbox_buttons)

    def _current_changed(self, index):
        # Lazily load the stacked widget.
        if self._widgets[index] is None:
            self._widgets[index] = SettingsWidget(self._controller.arguments,
                                                  self._components[index])
            self._widgets[index].parentClicked.connect(self._goto_parent)
            self._containers[index].setWidget(self._widgets[index])

        self._scroll_to_match()

    def _goto_parent(self, parent):
        i = self._components.index(parent)
        self._listWidget.setCurrentRow(i)

    def _save(self):
        flat_settings = {}
        disallowed = []
        for i, widget in enumerate(self._widgets):
            if widget is not None:
                values, allowed = widget.get_values()
                flat_settings.update(values)
                disallowed.extend([(i, key) for key, value in allowed.iteritems() if not value])

        pretty_json = json.dumps(flat_settings, indent=4, sort_keys=True)

        dialog = QtGui.QDialog(self._controller.central_widget)
        dialog.setWindowTitle("Confirm save")

        textEdit = QtGui.QTextEdit()
        textEdit.setPlainText(pretty_json)
        textEdit.setReadOnly(True)

        warnLayout = QtGui.QVBoxLayout()
        for i, key in disallowed:
            warnLayout.addWidget(QtGui.QLabel("Setting '{}' from component '{}' has incorrect value.".format(key, self._components[i])))

        groupWarnings = QtGui.QGroupBox("Warnings")
        groupWarnings.setLayout(warnLayout)

        scrollWarnings = QtGui.QScrollArea()
        scrollWarnings.setWidgetResizable(True)
        scrollWarnings.setWidget(groupWarnings)

        groundCheckBox = QtGui.QCheckBox("Ground station")
        groundCheckBox.setChecked(True)
        vehicleCheckBoxes = {}
        try:
            devices = self._controller.get_view_data(Control_Panel_View_Name.DEVICES, "devices")
        except KeyError:
            devices = []

        for vehicle in xrange(1, self._controller.xbee.number_of_sensors + 1):
            if vehicle < len(devices):
                vehicleJoined = devices[vehicle].joined
            else:
                vehicleJoined = True

            vehicleCheckBox = QtGui.QCheckBox("Vehicle {}".format(vehicle))
            vehicleCheckBox.setChecked(vehicleJoined)
            vehicleCheckBox.setEnabled(vehicleJoined)

            vehicleCheckBoxes[vehicle] = vehicleCheckBox

        boxLayout = QtGui.QVBoxLayout()
        boxLayout.addWidget(groundCheckBox)
        for vehicle in xrange(1, self._controller.xbee.number_of_sensors + 1):
            boxLayout.addWidget(vehicleCheckBoxes[vehicle])

        groupBox = QtGui.QGroupBox("Save locations")
        groupBox.setLayout(boxLayout)

        scrollBox = QtGui.QScrollArea()
        scrollBox.setWidgetResizable(True)
        scrollBox.setWidget(groupBox)

        dialogButtons = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        dialogButtons.accepted.connect(dialog.accept)
        dialogButtons.rejected.connect(dialog.reject)

        dialogLayout = QtGui.QVBoxLayout()
        dialogLayout.addWidget(textEdit)
        if disallowed:
            dialogLayout.addWidget(scrollWarnings)
        dialogLayout.addWidget(scrollBox)
        dialogLayout.addWidget(dialogButtons)

        dialog.setLayout(dialogLayout)

        result = dialog.exec_()
        if result != QtGui.QDialog.Accepted:
            return

        self._new_settings = flat_settings

        vehicle_settings = {}
        keys = sorted(self._new_settings.keys())
        count = 0
        for vehicle in xrange(1, self._controller.xbee.number_of_sensors + 1):
            if vehicleCheckBoxes[vehicle].isChecked():
                vehicle_settings[vehicle] = keys
                count += len(keys)

        if not vehicle_settings:
            if groundCheckBox.isChecked():
                self._set_ground_station_settings()

            return

        configuration = {
            "name": "setting",
            "clear_message": "setting_clear",
            "add_callback": self._make_add_setting_packet,
            "done_message": "setting_done",
            "ack_message": "setting_ack",
            "max_retries": self._settings.get("settings_max_retries"),
            "retry_interval": self._settings.get("settings_retry_interval")
        }
        sender = Control_Panel_XBee_Sender(self._controller, vehicle_settings,
                                           count, configuration)

        if groundCheckBox.isChecked():
            sender.connect_accepted(self._set_ground_station_settings)

        sender.start()

    def _make_add_setting_packet(self, vehicle, index, key):
        packet = XBee_Packet()
        packet.set("specification", "setting_add")
        packet.set("index", index)
        packet.set("key", str(key))
        packet.set("value", self._new_settings[key])
        packet.set("to_id", vehicle)

        return packet

    def _set_ground_station_settings(self):
        with open(self._controller.arguments.settings_file, 'w') as json_file:
            json.dump(self._new_settings, json_file, indent=4, sort_keys=True)

        Settings.settings_files = {}
        self._controller.arguments.groups = {}
        self._controller.load_settings()

    def _scroll_to_match(self):
        self._listWidget.scrollToItem(self._listWidget.currentItem())

        index = self._listWidget.currentRow()
        if index in self._best_matches:
            key = self._best_matches[index]
            settings_widget = self._widgets[index]
            try:
                widget = settings_widget.get_setting_widget(key)
            except KeyError:
                return

            self._stackedLayout.currentWidget().ensureWidgetVisible(widget)

    def _filter(self, text):
        text = text.toLower()
        self._best_matches = {}
        for i, component in enumerate(self._components):
            if text == "":
                hidden = False
            elif self._match_component(i, component, text):
                hidden = False
            else:
                hidden = True

            self._listWidget.item(i).setHidden(hidden)

        if len(self._best_matches) >= 1:
            keys = sorted(self._best_matches.keys())
            if keys[0] != self._listWidget.currentRow():
                self._listWidget.setCurrentRow(keys[0])

        self._scroll_to_match()

    def _match_component(self, index, component, text):
        if text in component:
            self._best_matches[index] = True
            return True

        settings = self._controller.arguments.get_settings(component)
        if text in settings.name.lower():
            self._best_matches[index] = True
            return True

        bestMatch = None
        for key, info in settings.get_info():
            matchType = self._match_setting(key, info, str(text))
            if matchType != Setting_Filter_Match.NONE:
                if bestMatch is None or matchType < bestMatch[0]:
                    bestMatch = (matchType, key)

        if bestMatch:
            self._best_matches[index] = bestMatch[1]
            return True

        return False

    def _match_setting(self, key, info, text):
        if text in key.lower():
            return Setting_Filter_Match.KEY
        if text in str(info["value"]).lower():
            return Setting_Filter_Match.VALUE
        if text in info["help"].lower():
            return Setting_Filter_Match.HELP

        return Setting_Filter_Match.NONE
