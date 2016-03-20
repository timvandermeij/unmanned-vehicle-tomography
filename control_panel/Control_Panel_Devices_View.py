from PyQt4 import QtGui
from Control_Panel_View import Control_Panel_View

class XBee_Device_Category(object):
    COORDINATOR = 0
    END_DEVICE = 2

class XBee_Device(object):
    def __init__(self, name, id, category, address, joined):
        self.name = name
        self.id = id
        self.category = category
        self.address = address
        self.joined = joined

class Control_Panel_Devices_View(Control_Panel_View):
    def show(self):
        """
        Show the devices view.
        """

        self._add_menu_bar()

        # Create the tree view.
        self._tree_view = QtGui.QTreeWidget()

        # Create the header for the tree view.
        header = QtGui.QTreeWidgetItem(["Device", "Property value"])
        self._tree_view.setHeaderItem(header)
        self._tree_view.header().setResizeMode(0, QtGui.QHeaderView.Stretch);

        # Fill the tree view with the devices.
        self._devices = [
            XBee_Device("Ground station", 0, XBee_Device_Category.COORDINATOR, "12:34:56:78:9A:BC", True),
            XBee_Device("Vehicle 1", 1, XBee_Device_Category.END_DEVICE, "DE:F1:23:45:67:89", False),
            XBee_Device("Vehicle 2", 2, XBee_Device_Category.END_DEVICE, "AB:CD:EF:12:34:56", False)
        ]
        self._fill()

        # Create the refresh button.
        refresh_button = QtGui.QPushButton("Refresh")
        refresh_button.clicked.connect(lambda: self._refresh())

        # Create the layout and add the widgets.
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(refresh_button)
        hbox.addStretch(1)

        vbox = QtGui.QVBoxLayout(self._controller.central_widget)
        vbox.addLayout(hbox)
        vbox.addWidget(self._tree_view)

    def _fill(self):
        """
        Fill the tree view with the device information.
        """

        categories = {
            XBee_Device_Category.COORDINATOR: "Coordinator",
            XBee_Device_Category.END_DEVICE: "End device"
        }

        # Add an entry in the tree view for each device.
        for device in self._devices:
            item = QtGui.QTreeWidgetItem(self._tree_view, [device.name])
            item_id = QtGui.QTreeWidgetItem(item, ["ID", str(device.id)])
            item_category = QtGui.QTreeWidgetItem(item, ["Category", categories[device.category]])
            item_address = QtGui.QTreeWidgetItem(item, ["Address", device.address])
            item_joined = QtGui.QTreeWidgetItem(item, ["Joined", "Yes" if device.joined else "No"])

        # Expand all items in the tree view.
        self._tree_view.expandToDepth(0)

    def _refresh(self):
        """
        Refresh the status of the ground station and the vehicles.
        """

        # TODO: update ground station status
        # TODO: update vehicle status using node discovery
        self._tree_view.clear()
        self._fill()
