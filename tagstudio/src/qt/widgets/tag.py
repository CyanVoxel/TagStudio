# Copyright (C) 2024 Travis Abendshien (CyanVoxel).
# Licensed under the GPL-3.0 License.
# Created for TagStudio: https://github.com/CyanVoxel/TagStudio


import math
import os
from types import FunctionType
from pathlib import Path

from PIL import Image
from PySide6.QtCore import Signal, Qt, QEvent
from PySide6.QtGui import QEnterEvent, QAction
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton

from src.core.library import Library, Tag
from src.core.palette import ColorType, get_tag_color


ERROR = f'[ERROR]'
WARNING = f'[WARNING]'
INFO = f'[INFO]'


class TagWidget(QWidget):
	edit_icon_128: Image.Image = Image.open(os.path.normpath(
		f'{Path(__file__).parent.parent.parent.parent}/resources/qt/images/edit_icon_128.png')).resize((math.floor(14*1.25),math.floor(14*1.25)))
	edit_icon_128.load()
	on_remove = Signal()
	on_click = Signal()
	on_edit = Signal()
	on_delete = Signal()

	def __init__(self, library:Library, tag:Tag, has_edit:bool, has_remove:bool, has_delete:bool, on_remove_callback:FunctionType=None, on_click_callback:FunctionType=None, on_edit_callback:FunctionType=None) -> None:
		super().__init__()
		self.lib = library
		self.tag = tag
		self.has_edit:bool = has_edit
		self.has_remove:bool = has_remove
		# self.bg_label = QLabel()
		# self.setStyleSheet('background-color:blue;')
		
		# if on_click_callback:
		self.setCursor(Qt.CursorShape.PointingHandCursor)
		self.base_layout = QVBoxLayout(self)
		self.base_layout.setObjectName('baseLayout')
		self.base_layout.setContentsMargins(0, 0, 0, 0)

		self.bg_button = QPushButton(self)
		self.bg_button.setFlat(True)
		self.bg_button.setText(tag.display_name(self.lib).replace('&', '&&'))
		if has_edit:
			edit_action = QAction('Edit', self)
			edit_action.triggered.connect(on_edit_callback)
			edit_action.triggered.connect(self.on_edit.emit)
			self.bg_button.addAction(edit_action)
		# if on_click_callback:
		self.bg_button.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
		# if has_remove:
		# 	remove_action = QAction('Remove', self)
		# 	# remove_action.triggered.connect(on_remove_callback)
		# 	remove_action.triggered.connect(self.on_remove.emit())
		# 	self.bg_button.addAction(remove_action)
		search_for_tag_action = QAction('Search for Tag', self)
		# search_for_tag_action.triggered.connect(on_click_callback)
		search_for_tag_action.triggered.connect(self.on_click.emit)
		self.bg_button.addAction(search_for_tag_action)
		add_to_search_action = QAction('Add to Search', self)
		self.bg_button.addAction(add_to_search_action)
		
		if has_delete:
			delete_action = QAction('Delete Tag', self)
			delete_action.triggered.connect(self.on_delete.emit)
			self.bg_button.addAction(delete_action)

		self.inner_layout = QHBoxLayout()
		self.inner_layout.setObjectName('innerLayout')
		self.inner_layout.setContentsMargins(2, 2, 2, 2)
		# self.inner_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
		
		# self.inner_container = QWidget()
		# self.inner_container.setLayout(self.inner_layout)
		# self.base_layout.addWidget(self.inner_container)
		self.bg_button.setLayout(self.inner_layout)
		self.bg_button.setMinimumSize(math.ceil(22*1.5), 22)

		# self.bg_button.setStyleSheet(
		# 	f'QPushButton {{'
		# 	f'border: 2px solid #8f8f91;'
		# 	f'border-radius: 6px;'
		# 	f'background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,stop: 0 {ColorType.PRIMARY}, stop: 1 {ColorType.BORDER});'
		# 	f'min-width: 80px;}}')

		self.bg_button.setStyleSheet(
									# f'background: {get_tag_color(ColorType.PRIMARY, tag.color)};'
									f'QPushButton{{'
										f'background: {get_tag_color(ColorType.PRIMARY, tag.color)};'
										# f'background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {get_tag_color(ColorType.PRIMARY, tag.color)}, stop:1.0 {get_tag_color(ColorType.BORDER, tag.color)});'
										# f"border-color:{get_tag_color(ColorType.PRIMARY, tag.color)};"
										f"color: {get_tag_color(ColorType.TEXT, tag.color)};"
										f'font-weight: 600;'
										f"border-color:{get_tag_color(ColorType.BORDER, tag.color)};"
										f'border-radius: 6px;'
										f'border-style:solid;'
										f'border-width: {math.ceil(1*self.devicePixelRatio())}px;'
										# f'border-top:2px solid {get_tag_color(ColorType.LIGHT_ACCENT, tag.color)};'
										# f'border-bottom:2px solid {get_tag_color(ColorType.BORDER, tag.color)};'
										# f'border-left:2px solid {get_tag_color(ColorType.BORDER, tag.color)};'
										# f'border-right:2px solid {get_tag_color(ColorType.BORDER, tag.color)};'
										# f'padding-top: 0.5px;'
										f'padding-right: 4px;'
										f'padding-bottom: 1px;'
										f'padding-left: 4px;'
										f'font-size: 13px'
										f'}}'
										f'QPushButton::hover{{'
										# f'background: {get_tag_color(ColorType.LIGHT_ACCENT, tag.color)};'
										# f'background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {get_tag_color(ColorType.PRIMARY, tag.color)}, stop:1.0 {get_tag_color(ColorType.BORDER, tag.color)});'
										# f"border-color:{get_tag_color(ColorType.PRIMARY, tag.color)};"
										# f"color: {get_tag_color(ColorType.TEXT, tag.color)};"
										f"border-color:{get_tag_color(ColorType.LIGHT_ACCENT, tag.color)};"
										f'}}')

		# self.renderer = ThumbRenderer()
		# self.renderer.updated.connect(lambda ts, i, s, ext: (self.update_thumb(ts, image=i),
		# 													 self.update_size(
		# 														 ts, size=s),
		# 													 self.set_extension(ext)))
		
		# self.bg_button.setLayout(self.base_layout)
		
		self.base_layout.addWidget(self.bg_button)
		# self.setMinimumSize(self.bg_button.size())

		# logging.info(tag.color)
		if has_remove:
			self.remove_button = QPushButton(self)
			self.remove_button.setFlat(True)
			self.remove_button.setText('–')
			self.remove_button.setHidden(True)
			self.remove_button.setStyleSheet(f'color: {get_tag_color(ColorType.PRIMARY, tag.color)};'
										f"background: {get_tag_color(ColorType.TEXT, tag.color)};"
										# f"color: {'black' if color not in ['black', 'gray', 'dark gray', 'cool gray', 'warm gray', 'blue', 'purple', 'violet'] else 'white'};"
										# f"border-color: {get_tag_color(ColorType.BORDER, tag.color)};"
										f'font-weight: 800;'
										# f"border-color:{'black' if color not in [
										# 'black', 'gray', 'dark gray', 
										# 'cool gray', 'warm gray', 'blue', 
										# 'purple', 'violet'] else 'white'};"
										f'border-radius: 4px;'
										# f'border-style:solid;'
										f'border-width:0;'
										# f'padding-top: 1.5px;'
										# f'padding-right: 4px;'
										f'padding-bottom: 4px;'
										# f'padding-left: 4px;'
										f'font-size: 14px')
			self.remove_button.setMinimumSize(19,19)
			self.remove_button.setMaximumSize(19,19)
			# self.remove_button.clicked.connect(on_remove_callback)
			self.remove_button.clicked.connect(self.on_remove.emit)

		# NOTE: No more edit button! Just make it a right-click option.
		# self.edit_button = QPushButton(self)
		# self.edit_button.setFlat(True)
		# self.edit_button.setText('Edit')
		# self.edit_button.setIcon(QPixmap.fromImage(ImageQt.ImageQt(self.edit_icon_128)))
		# self.edit_button.setIconSize(QSize(14,14))
		# self.edit_button.setHidden(True)
		# self.edit_button.setStyleSheet(f'color: {color};'
		# 						    f"background: {'black' if color not in ['black', 'gray', 'dark gray', 'cool gray', 'warm gray', 'blue', 'purple', 'violet'] else 'white'};"
		# 							# f"color: {'black' if color not in ['black', 'gray', 'dark gray', 'cool gray', 'warm gray', 'blue', 'purple', 'violet'] else 'white'};"
		# 							f"border-color: {'black' if color not in ['black', 'gray', 'dark gray', 'cool gray', 'warm gray', 'blue', 'purple', 'violet'] else 'white'};"
		# 							f'font-weight: 600;'
		# 							# f"border-color:{'black' if color not in [
		# 							# 'black', 'gray', 'dark gray', 
		# 							# 'cool gray', 'warm gray', 'blue', 
		# 							# 'purple', 'violet'] else 'white'};"
		# 							# f'QPushButton{{border-image: url(:/images/edit_icon_128.png);}}'
		# 							# f'QPushButton{{border-image: url(:/images/edit_icon_128.png);}}'
		# 							f'border-radius: 4px;'
		# 							# f'border-style:solid;'
		# 							# f'border-width:1px;'
		# 							f'padding-top: 1.5px;'
		# 							f'padding-right: 4px;'
		# 							f'padding-bottom: 3px;'
		# 							f'padding-left: 4px;'
		# 							f'font-size: 14px')
		# self.edit_button.setMinimumSize(18,18)
		# # self.edit_button.setMaximumSize(18,18)


		# self.inner_layout.addWidget(self.edit_button)
		if has_remove:
			self.inner_layout.addWidget(self.remove_button)
		self.inner_layout.addStretch(1)
		

		# NOTE: Do this if you don't want the tag to stretch, like in a search.
		# self.bg_button.setMaximumWidth(self.bg_button.sizeHint().width())
		
		# self.set_click(on_click_callback)
		self.bg_button.clicked.connect(self.on_click.emit)

		# self.setMinimumSize(50,20)

	# def set_name(self, name:str):
	# 	self.bg_label.setText(str)

	# def on_remove(self):
	# 	if self.item and self.item[0] == ItemType.ENTRY:
	# 		if self.field_index >= 0:
	# 			self.lib.get_entry(self.item[1]).remove_tag(self.tag.id, self.field_index)
	# 		else:
	# 			self.lib.get_entry(self.item[1]).remove_tag(self.tag.id)

	# def set_click(self, callback):
	# 	try:
	# 		self.bg_button.clicked.disconnect()
	# 	except RuntimeError:
	# 		pass
	# 	if callback:
	# 		self.bg_button.clicked.connect(callback)

	# def set_click(self, function):
	# 	try:
	# 		self.bg.clicked.disconnect()
	# 	except RuntimeError:
	# 		pass
	# 	# self.bg.clicked.connect(lambda checked=False, filepath=filepath: open_file(filepath))
	# 	# self.bg.clicked.connect(function)
	
	def enterEvent(self, event: QEnterEvent) -> None:
		if self.has_remove:
			self.remove_button.setHidden(False)
		# self.edit_button.setHidden(False)
		self.update()
		return super().enterEvent(event)

	def leaveEvent(self, event: QEvent) -> None:
		if self.has_remove:
			self.remove_button.setHidden(True)
		# self.edit_button.setHidden(True)
		self.update()
		return super().leaveEvent(event)
