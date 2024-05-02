# Copyright (C) 2024 Travis Abendshien (CyanVoxel).
# Licensed under the GPL-3.0 License.
# Created for TagStudio: https://github.com/CyanVoxel/TagStudio


import logging
import math
import typing

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QPushButton, QMessageBox, QApplication

from src.core.library import Library, Tag
from src.qt.flowlayout import FlowLayout
from src.qt.widgets import FieldWidget, TagWidget, PanelModal
from src.qt.modals import BuildTagPanel, TagSearchPanel

# Only import for type checking/autocompletion, will not be imported at runtime.
if typing.TYPE_CHECKING:
	from src.qt.ts_qt import QtDriver


class TagBoxWidget(FieldWidget):
	updated = Signal()
	
	def __init__(self, item, title, field_index, library:Library, tags:list[int], driver:'QtDriver') -> None:
		super().__init__(title)
		# QObject.__init__(self)
		self.item = item
		self.lib = library
		self.driver = driver # Used for creating tag click callbacks that search entries for that tag. 
		self.field_index = field_index
		self.tags:list[int] = tags
		self.setObjectName('tagBox')
		self.base_layout = FlowLayout()
		self.base_layout.setGridEfficiency(False)
		self.base_layout.setContentsMargins(0, 0, 0, 0)
		self.setLayout(self.base_layout)

		self.add_button = QPushButton()
		self.add_button.setCursor(Qt.CursorShape.PointingHandCursor)
		self.add_button.setMinimumSize(23, 23)
		self.add_button.setMaximumSize(23, 23)
		self.add_button.setText('+')
		self.add_button.setStyleSheet(
									f'QPushButton{{'
									# f'background: #1E1A33;'
									# f'color: #CDA7F7;'
									f'font-weight: bold;'
									# f"border-color: #2B2547;"
									f'border-radius: 6px;'
									f'border-style:solid;'
									f'border-width:{math.ceil(1*self.devicePixelRatio())}px;'
									# f'padding-top: 1.5px;'
									# f'padding-right: 4px;'
									f'padding-bottom: 5px;'
									# f'padding-left: 4px;'
									f'font-size: 20px;'
									f'}}'
									f'QPushButton::hover'
									f'{{'
									# f'background: #2B2547;'
									f'}}')
		tsp = TagSearchPanel(self.lib)
		tsp.tag_chosen.connect(lambda x: self.add_tag_callback(x))
		self.add_modal = PanelModal(tsp, title, 'Add Tags')
		self.add_button.clicked.connect(self.add_modal.show)

		self.set_tags(tags)
		# self.add_button.setHidden(True)

	def set_item(self, item):
		self.item = item
	
	def update_tags(self):
		is_recycled = False
		
		if self.base_layout.itemAt(0):
			# logging.info(type(self.base_layout.itemAt(0).widget()))
			is_recycled = True
			while self.base_layout.itemAt(0) and self.base_layout.itemAt(1):
				# logging.info(f"I'm deleting { self.base_layout.itemAt(0).widget()}")
				self.base_layout.takeAt(0).widget().deleteLater()
		
		for tag_id in self.tags:
			# TODO: Remove space from the special search here (tag_id:x) once that system is finalized.
			# tw = TagWidget(self.lib, self.lib.get_tag(tag), True, True, 
			# 							on_remove_callback=lambda checked=False, t=tag: (self.lib.get_entry(self.item.id).remove_tag(self.lib, t, self.field_index), self.updated.emit()), 
			# 							on_click_callback=lambda checked=False, q=f'tag_id: {tag}': (self.driver.main_window.searchField.setText(q), self.driver.filter_items(q)),
			# 							on_edit_callback=lambda checked=False, t=tag: (self.edit_tag(t))
			# 							)
			tag_deletable = tag_id not in [0, 1] # [0, 1] should probably be extracted as a constant during refactor
			tw = TagWidget(self.lib, self.lib.get_tag(tag_id), True, True, tag_deletable)
			tw.on_click.connect(lambda checked=False, q=f'tag_id: {tag_id}': (self.driver.main_window.searchField.setText(q), self.driver.filter_items(q)))
			tw.on_remove.connect(lambda checked=False, t=tag_id: (self.remove_tag(t)))
			tw.on_edit.connect(lambda checked=False, t=tag_id: (self.edit_tag(t)))
			tw.on_delete.connect(lambda checked=False, t=tag_id: (self.delete_tag(t)))
			self.base_layout.addWidget(tw)
		
		# Move or add the '+' button.
		if is_recycled:
			self.base_layout.addWidget(self.base_layout.takeAt(0).widget())
		else:
			self.base_layout.addWidget(self.add_button)
	
	def set_tags(self, tags:list[int]):
		logging.info(f'[TAG BOX WIDGET] SET TAGS: T:{tags} for E:{self.item.id}')
		self.tags = tags
		self.update_tags()
		
		# Handles an edge case where there are no more tags and the '+' button
		# doesn't move all the way to the left.
		if self.base_layout.itemAt(0) and not self.base_layout.itemAt(1):
			self.base_layout.update()


	def edit_tag(self, tag_id:int):
		btp = BuildTagPanel(self.lib, tag_id)
		# btp.on_edit.connect(lambda x: self.edit_tag_callback(x))
		self.edit_modal = PanelModal(btp, 
							   self.lib.get_tag(tag_id).display_name(self.lib), 
							   'Edit Tag',
							   done_callback=(self.driver.preview_panel.update_widgets),
							   has_save=True)
		# self.edit_modal.widget.update_display_name.connect(lambda t: self.edit_modal.title_widget.setText(t))
		panel: BuildTagPanel = self.edit_modal.widget
		self.edit_modal.saved.connect(lambda: self.lib.update_tag(btp.build_tag()))
		# panel.tag_updated.connect(lambda tag: self.lib.update_tag(tag))
		self.edit_modal.show()
	
	
	def delete_tag(self, tag_id:int):
		def show_delete_prompt() -> bool:
			result = QMessageBox.question(self, "Delete Tag", f"Are you sure you want to delete Tag {tag.name}?",
								 QMessageBox.Yes | QMessageBox.No)
			
			return result == QMessageBox.Yes
		
		tag = self.lib.get_tag(tag_id)
		shift_held = Qt.KeyboardModifier.ShiftModifier in QApplication.keyboardModifiers()
		
		if shift_held or show_delete_prompt():
			self.lib.remove_tag(tag_id)
			self.update_tags()
			
			if not shift_held:
				QMessageBox.information(self, "Delete Tag", "Tag deleted.")


	def add_tag_callback(self, tag_id):
		# self.base_layout.addWidget(TagWidget(self.lib, self.lib.get_tag(tag), True))
		# self.tags.append(tag)
		logging.info(f'[TAG BOX WIDGET] ADD TAG CALLBACK: T:{tag_id} to E:{self.item.id}')
		logging.info(f'[TAG BOX WIDGET] SELECTED T:{self.driver.selected}')
		id = list(self.field.keys())[0]
		for x in self.driver.selected:
				self.driver.lib.get_entry(x[1]).add_tag(self.driver.lib, tag_id, field_id=id, field_index=-1)
				self.updated.emit()
		if tag_id == 0 or tag_id == 1:
			self.driver.update_badges()

		# if type((x[0]) == ThumbButton):
		# 	# TODO: Remove space from the special search here (tag_id:x) once that system is finalized.
			# logging.info(f'I want to add tag ID {tag_id} to entry {self.item.filename}')
			# self.updated.emit()
			# if tag_id not in self.tags:
			# 	self.tags.append(tag_id)
			# self.set_tags(self.tags)
		# elif type((x[0]) == ThumbButton):

	
	def edit_tag_callback(self, tag:Tag):
		self.lib.update_tag(tag)
		
	def remove_tag(self, tag_id):
		logging.info(f'[TAG BOX WIDGET] SELECTED T:{self.driver.selected}')
		id = list(self.field.keys())[0]
		for x in self.driver.selected:
			index = self.driver.lib.get_field_index_in_entry(self.driver.lib.get_entry(x[1]),id)
			self.driver.lib.get_entry(x[1]).remove_tag(self.driver.lib, tag_id,field_index=index[0])
			self.updated.emit()
		if tag_id == 0 or tag_id == 1:
			self.driver.update_badges()

	# def show_add_button(self, value:bool):
	# 	self.add_button.setHidden(not value)
