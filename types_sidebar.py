# Copyright (c) 2015-2022 Vector 35 Inc
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from binaryninja import Platform, TypeParserResult, Type, TypeClass, ThemeColor
from binaryninjaui import SidebarWidget, SidebarWidgetType, Sidebar, UIActionHandler, getMonospaceFont, getThemeColor
from PySide6 import QtCore
from PySide6.QtCore import Qt, QRectF, QSettings
from PySide6.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout, QLabel, QWidget, QPushButton, QMenu, QSplitter, \
	QTextEdit, QTreeWidget, QTreeWidgetItem
from PySide6.QtGui import QImage, QPixmap, QPainter, QFont, QColor, QFontMetrics

instance_id = 0


class TypesSidebarWidget(SidebarWidget):
	def __init__(self, name, frame, data):
		global instance_id
		SidebarWidget.__init__(self, name)
		self.actionHandler = UIActionHandler()
		self.actionHandler.setupActionHandler(self)
		self.layout = QVBoxLayout(self)
		self.layout.addWidget(QLabel("Platform:"))
		self.platformEntry = QPushButton(self)
		self.platformMenu = QMenu(self)
		for platform in Platform:
			def select_platform(platform):
				return lambda: self.selectPlatform(platform)
			self.platformMenu.addAction(platform.name, select_platform(platform))

		self.platform = Platform['windows-x86_64']
		self.platformEntry.setText('windows-x86_64')  # todo prefs
		self.platformEntry.setMenu(self.platformMenu)
		self.layout.addWidget(self.platformEntry)

		splitter = QSplitter(Qt.Orientation.Vertical)
		self.layout.addWidget(splitter)

		font = getMonospaceFont(self)
		self.typesBox = QTextEdit()
		self.typesBox.setPlainText(QSettings().value("plugin.typeInspector.types"))
		self.typesBox.setFont(font)
		self.typesBox.setTabStopDistance(QFontMetrics(font).horizontalAdvance(" ") * 4)
		splitter.addWidget(self.typesBox)
		self.typesBox.textChanged.connect(self.updateTypes)

		self.errorBox = QLabel()
		self.errorBox.setWordWrap(True)
		splitter.addWidget(self.errorBox)

		self.typesTree = QTreeWidget()
		self.typesTree.setColumnCount(2)
		self.typesTree.setIndentation(10)
		splitter.addWidget(self.typesTree)

		splitter.setSizes([1000, 1, 1000])

		self.selectPlatform(self.platform)

	def notifyOffsetChanged(self, offset):
		self.offset.setText(hex(offset))

	def notifyViewChanged(self, view_frame):
		pass

	def contextMenuEvent(self, event):
		self.m_contextMenuManager.show(self.m_menu, self.actionHandler)

	def selectPlatform(self, platform):
		self.platform = platform
		self.updateTypes()
		# Load base types
		try:
			self.platform.parse_types_from_source('')
		except SyntaxError:
			pass

	def updateTypes(self):
		conts = self.typesBox.toPlainText()
		conts = conts.replace('\x00', '')  # What
		QSettings().setValue("plugin.typeInspector.types", conts)
		try:
			result: TypeParserResult = self.platform.parse_types_from_source(conts)
			scroll_x = self.typesTree.horizontalScrollBar().value()
			scroll_y = self.typesTree.verticalScrollBar().value()
			self.typesTree.clear()
			self.typesBox.blockSignals(True)
			pos = self.typesBox.textCursor().position()
			self.typesBox.setTextColor(self.palette().text().color())
			self.typesBox.setPlainText(conts)
			c = self.typesBox.textCursor()
			c.setPosition(pos)
			self.typesBox.setTextCursor(c)
			self.typesBox.blockSignals(False)

			def boolstr(b: bool):
				if b:
					return "True"
				return "False"

			def create_type_tree(root: QTreeWidgetItem, type: Type):
				if type.type_class == TypeClass.VoidTypeClass:
					tree = QTreeWidgetItem(["void"])
					root.addChild(tree)
					tree.addChild(QTreeWidgetItem(["width", hex(type.width)]))
					tree.addChild(QTreeWidgetItem(["alignment", hex(type.alignment)]))
				elif type.type_class == TypeClass.BoolTypeClass:
					tree = QTreeWidgetItem(["bool"])
					root.addChild(tree)
					tree.addChild(QTreeWidgetItem(["width", hex(type.width)]))
					tree.addChild(QTreeWidgetItem(["alignment", hex(type.alignment)]))
				elif type.type_class == TypeClass.IntegerTypeClass:
					tree = QTreeWidgetItem(["int"])
					root.addChild(tree)
					tree.addChild(QTreeWidgetItem(["width", hex(type.width)]))
					tree.addChild(QTreeWidgetItem(["alignment", hex(type.alignment)]))
					tree.addChild(QTreeWidgetItem(["signed", boolstr(type.signed)]))
				elif type.type_class == TypeClass.FloatTypeClass:
					tree = QTreeWidgetItem(["float"])
					root.addChild(tree)
					tree.addChild(QTreeWidgetItem(["width", hex(type.width)]))
					tree.addChild(QTreeWidgetItem(["alignment", hex(type.alignment)]))
				elif type.type_class == TypeClass.StructureTypeClass:
					tree = QTreeWidgetItem(["struct"])
					root.addChild(tree)
					tree.addChild(QTreeWidgetItem(["width", hex(type.width)]))
					tree.addChild(QTreeWidgetItem(["alignment", hex(type.alignment)]))
					tree.addChild(QTreeWidgetItem(["type", str(type.type)]))
					tree.addChild(QTreeWidgetItem(["packed", boolstr(type.packed)]))
					members = QTreeWidgetItem(["members"])
					tree.addChild(members)
					for m in type.members:
						member = QTreeWidgetItem([m.name, hex(m.offset)])
						create_type_tree(member, m.type)
						members.addChild(member)
				elif type.type_class == TypeClass.EnumerationTypeClass:
					tree = QTreeWidgetItem(["enum"])
					root.addChild(tree)
					tree.addChild(QTreeWidgetItem(["width", hex(type.width)]))
					tree.addChild(QTreeWidgetItem(["alignment", hex(type.alignment)]))
					members = QTreeWidgetItem(["members"])
					tree.addChild(members)
					for m in type.members:
						member = QTreeWidgetItem([m.name, hex(m.offset)])
						create_type_tree(member, m.type)
						members.addChild(member)
				elif type.type_class == TypeClass.PointerTypeClass:
					tree = QTreeWidgetItem(["pointer"])
					root.addChild(tree)
					tree.addChild(QTreeWidgetItem(["width", hex(type.width)]))
					tree.addChild(QTreeWidgetItem(["alignment", hex(type.alignment)]))
					target = QTreeWidgetItem(["target"])
					tree.addChild(target)
					create_type_tree(target, type.target)
				elif type.type_class == TypeClass.ArrayTypeClass:
					tree = QTreeWidgetItem(["array"])
					root.addChild(tree)
					tree.addChild(QTreeWidgetItem(["width", hex(type.width)]))
					tree.addChild(QTreeWidgetItem(["alignment", hex(type.alignment)]))
					tree.addChild(QTreeWidgetItem(["count", hex(type.count)]))
					element_type = QTreeWidgetItem(["element_type"])
					tree.addChild(element_type)
					create_type_tree(element_type, type.element_type)
				elif type.type_class == TypeClass.FunctionTypeClass:
					tree = QTreeWidgetItem(["function"])
					root.addChild(tree)
					tree.addChild(QTreeWidgetItem(["width", hex(type.width)]))
					tree.addChild(QTreeWidgetItem(["alignment", hex(type.alignment)]))
					tree.addChild(QTreeWidgetItem(["stack_adjustment", hex(type.stack_adjustment.value)]))
					if type.calling_convention is not None:
						tree.addChild(QTreeWidgetItem(["calling_convention", type.calling_convention.name]))
					else:
						tree.addChild(QTreeWidgetItem(["calling_convention", "None"]))
					tree.addChild(QTreeWidgetItem(["has_variable_arguments", boolstr(type.has_variable_arguments.value)]))
					tree.addChild(QTreeWidgetItem(["can_return", boolstr(type.can_return.value)]))
					return_value = QTreeWidgetItem(["return_value"])
					tree.addChild(return_value)
					create_type_tree(return_value, type.return_value)
					parameters = QTreeWidgetItem(["parameters"])
					tree.addChild(parameters)
					for m in type.parameters:
						parameter = QTreeWidgetItem([m.name, hex(m.offset)])
						create_type_tree(parameter, m.type)
						parameters.addChild(parameter)
				elif type.type_class == TypeClass.VarArgsTypeClass:
					tree = QTreeWidgetItem(["varargs"])
					root.addChild(tree)
					tree.addChild(QTreeWidgetItem(["width", hex(type.width)]))
					tree.addChild(QTreeWidgetItem(["alignment", hex(type.alignment)]))
				elif type.type_class == TypeClass.ValueTypeClass:
					tree = QTreeWidgetItem(["ValueTypeClass"])
					root.addChild(tree)
					tree.addChild(QTreeWidgetItem(["width", hex(type.width)]))
					tree.addChild(QTreeWidgetItem(["alignment", hex(type.alignment)]))
				elif type.type_class == TypeClass.NamedTypeReferenceClass:
					tree = QTreeWidgetItem(["named_type"])
					root.addChild(tree)
					tree.addChild(QTreeWidgetItem(["width", hex(type.width)]))
					tree.addChild(QTreeWidgetItem(["alignment", hex(type.alignment)]))
					tree.addChild(QTreeWidgetItem(["named_type_class", str(type.named_type_class)]))
					tree.addChild(QTreeWidgetItem(["type_id", type.type_id]))
					tree.addChild(QTreeWidgetItem(["name", str(type.name)]))
				elif type.type_class == TypeClass.WideCharTypeClass:
					tree = QTreeWidgetItem(["wchar"])
					root.addChild(tree)
					tree.addChild(QTreeWidgetItem(["width", hex(type.width)]))
					tree.addChild(QTreeWidgetItem(["alignment", hex(type.alignment)]))
				else:
					tree = QTreeWidgetItem(["???"])
					root.addChild(tree)
					tree.addChild(QTreeWidgetItem(["width", hex(type.width)]))
					tree.addChild(QTreeWidgetItem(["alignment", hex(type.alignment)]))

			types_tree = QTreeWidgetItem(self.typesTree, ["Types"])
			types_tree.setBackground(0, self.palette().alternateBase())
			types_tree.setBackground(1, self.palette().alternateBase())
			self.typesTree.addTopLevelItem(types_tree)

			for name, type in result.types.items():
				child = QTreeWidgetItem(types_tree, [str(name)])
				child.addChild(create_type_tree(child, type))
				types_tree.addChild(child)

			vars_tree = QTreeWidgetItem(self.typesTree, ["Variables"])
			vars_tree.setBackground(0, self.palette().alternateBase())
			vars_tree.setBackground(1, self.palette().alternateBase())
			self.typesTree.addTopLevelItem(vars_tree)

			for name, type in result.variables.items():
				child = QTreeWidgetItem(vars_tree, [str(name)])
				child.addChild(create_type_tree(child, type))
				vars_tree.addChild(child)

			funcs_tree = QTreeWidgetItem(self.typesTree, ["Functions"])
			funcs_tree.setBackground(0, self.palette().alternateBase())
			funcs_tree.setBackground(1, self.palette().alternateBase())
			self.typesTree.addTopLevelItem(funcs_tree)

			for name, type in result.functions.items():
				child = QTreeWidgetItem(funcs_tree, [str(name)])
				child.addChild(create_type_tree(child, type))
				funcs_tree.addChild(child)

			self.typesTree.expandAll()
			self.typesTree.resizeColumnToContents(0)
			self.typesTree.resizeColumnToContents(1)
			self.typesTree.horizontalScrollBar().setValue(scroll_x)
			self.typesTree.verticalScrollBar().setValue(scroll_y)

			self.errorBox.setText("")
		except SyntaxError as e:
			self.typesBox.blockSignals(True)
			pos = self.typesBox.textCursor().position()
			self.typesBox.setTextColor(getThemeColor(ThemeColor.RedStandardHighlightColor))
			self.typesBox.setPlainText(conts)
			c = self.typesBox.textCursor()
			c.setPosition(pos)
			self.typesBox.setTextCursor(c)
			self.typesBox.blockSignals(False)
			self.errorBox.setText(str(e))


class TypesSidebarWidgetType(SidebarWidgetType):
	def __init__(self):
		# Sidebar icons are 28x28 points. Should be at least 56x56 pixels for
		# HiDPI display compatibility. They will be automatically made theme
		# aware, so you need only provide a grayscale image, where white is
		# the color of the shape.
		icon = QImage(56, 56, QImage.Format_RGB32)
		icon.fill(0)

		# Render an "H" as the example icon
		p = QPainter()
		p.begin(icon)
		p.setFont(QFont("Open Sans", 56))
		p.setPen(QColor(255, 255, 255, 255))
		p.drawText(QRectF(0, 0, 56, 56), Qt.AlignCenter, "TI")
		p.end()

		SidebarWidgetType.__init__(self, icon, "Type Inspector")

	def createWidget(self, frame, data):
		return TypesSidebarWidget("Type Inspector", frame, data)

	def viewSensitive(self, *args, **kwargs):
		return False


Sidebar.addSidebarWidgetType(TypesSidebarWidgetType())
