# Copyright (C) 2024 Travis Abendshien (CyanVoxel).
# Licensed under the GPL-3.0 License.
# Created for TagStudio: https://github.com/CyanVoxel/TagStudio

"""A pagination widget created for TagStudio."""
# I never want to see this code again.

from PySide6.QtCore import QObject, QSize, Signal
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from src.core.logging import get_logger

logger = get_logger(__name__)


# class NumberEdit(QLineEdit):
# 	def __init__(self, parent=None) -> None:
# 		super().__init__(parent)
# 		self.textChanged


class Pagination(QWidget, QObject):
    """Widget containing controls for navigating between pages of items."""

    index = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.page_count: int = 0
        self.current_page_index: int = 0
        self.buffer_page_count: int = 4
        self.button_size = QSize(32, 24)

        # ------------ UI EXAMPLE --------------
        # [<] [1]...[3][4] [5] [6][7]...[42] [>]
        #            ^^^^ <-- 2 Buffer Pages
        # Center Page Number is Editable Text
        # --------------------------------------

        # [----------- ROOT LAYOUT ------------]
        self.setHidden(True)
        self.root_layout = QHBoxLayout(self)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        self.root_layout.setContentsMargins(0, 6, 0, 0)
        self.root_layout.setSpacing(3)
        # self.setMinimumHeight(32)

        # [<] ----------------------------------
        self.prev_button = QPushButton()
        self.prev_button.setText("<")
        self.prev_button.setMinimumSize(self.button_size)
        self.prev_button.setMaximumSize(self.button_size)

        # --- [1] ------------------------------
        self.start_button = QPushButton()
        self.start_button.setMinimumSize(self.button_size)
        self.start_button.setMaximumSize(self.button_size)
        # self.start_button.setStyleSheet('background:cyan;')
        # self.start_button.setMaximumHeight(self.button_size.height())

        # ------ ... ---------------------------
        self.start_ellipses = QLabel()
        self.start_ellipses.setMinimumSize(self.button_size)
        self.start_ellipses.setMaximumSize(self.button_size)
        # self.start_ellipses.setMaximumHeight(self.button_size.height())
        self.start_ellipses.setText(". . .")

        # --------- [3][4] ---------------------
        self.start_buffer_container = QWidget()
        self.start_buffer_layout = QHBoxLayout(self.start_buffer_container)
        self.start_buffer_layout.setContentsMargins(0, 0, 0, 0)
        self.start_buffer_layout.setSpacing(3)
        # self.start_buffer_container.setStyleSheet('background:blue;')

        # ---------------- [5] -----------------
        self.current_page_field = QLineEdit()
        self.current_page_field.setMinimumSize(self.button_size)
        self.current_page_field.setMaximumSize(self.button_size)
        self.validator = Validator(1, self.page_count)
        self.current_page_field.setValidator(self.validator)
        self.current_page_field.returnPressed.connect(
            lambda: self._goto_page(int(self.current_page_field.text()) - 1)
        )
        # self.current_page_field.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        # self.current_page_field.setMaximumHeight(self.button_size.height())
        # self.current_page_field.setMaximumWidth(self.button_size.width())

        # -------------------- [6][7] ----------
        self.end_buffer_container = QWidget()
        self.end_buffer_layout = QHBoxLayout(self.end_buffer_container)
        self.end_buffer_layout.setContentsMargins(0, 0, 0, 0)
        self.end_buffer_layout.setSpacing(3)
        # self.end_buffer_container.setStyleSheet('background:orange;')

        # -------------------------- ... -------
        self.end_ellipses = QLabel()
        self.end_ellipses.setMinimumSize(self.button_size)
        self.end_ellipses.setMaximumSize(self.button_size)
        # self.end_ellipses.setMaximumHeight(self.button_size.height())
        self.end_ellipses.setText(". . .")

        # ----------------------------- [42] ---
        self.end_button = QPushButton()
        self.end_button.setMinimumSize(self.button_size)
        self.end_button.setMaximumSize(self.button_size)
        # self.end_button.setMaximumHeight(self.button_size.height())
        # self.end_button.setStyleSheet('background:red;')

        # ---------------------------------- [>]
        self.next_button = QPushButton()
        self.next_button.setText(">")
        self.next_button.setMinimumSize(self.button_size)
        self.next_button.setMaximumSize(self.button_size)

        # Add Widgets to Root Layout
        self.root_layout.addStretch(1)
        self.root_layout.addWidget(self.prev_button)
        self.root_layout.addWidget(self.start_button)
        self.root_layout.addWidget(self.start_ellipses)
        self.root_layout.addWidget(self.start_buffer_container)
        self.root_layout.addWidget(self.current_page_field)
        self.root_layout.addWidget(self.end_buffer_container)
        self.root_layout.addWidget(self.end_ellipses)
        self.root_layout.addWidget(self.end_button)
        self.root_layout.addWidget(self.next_button)
        self.root_layout.addStretch(1)

        self._populate_buffer_buttons()
        # self.update_buttons(page_count=9, index=0)

    def update_buttons(self, page_count: int, index: int, emit: bool = True):
        # Guard
        if index < 0:
            raise ValueError("Negative index detected")

        # Screw it
        for i in range(0, 10):
            if self.start_buffer_layout.itemAt(i):
                self.start_buffer_layout.itemAt(i).widget().setHidden(True)
            if self.end_buffer_layout.itemAt(i):
                self.end_buffer_layout.itemAt(i).widget().setHidden(True)

        end_page = page_count - 1
        if page_count <= 1:
            # Hide everything if there are only one or less pages.
            # [-------------- HIDDEN --------------]
            self.setHidden(True)
        # elif page_count > 1 and page_count < 7:
        # 	# Only show Next/Prev, current index field, and both start and end
        # 	# buffers (the end may be odd).
        # 	# [<] [1][2][3][4][5][6] [>]
        # 	self.start_button.setHidden(True)
        # 	self.start_ellipses.setHidden(True)
        # 	self.end_ellipses.setHidden(True)
        # 	self.end_button.setHidden(True)
        # elif page_count > 1:
        # 	self.start_button.setHidden(False)
        # 	self.start_ellipses.setHidden(False)
        # 	self.end_ellipses.setHidden(False)
        # 	self.end_button.setHidden(False)

        # 	self.start_button.setText('1')
        # 	self.assign_click(self.start_button, 0)
        # 	self.end_button.setText(str(page_count))
        # 	self.assign_click(self.end_button, page_count-1)

        elif page_count > 1:
            # Enable/Disable Next+Prev Buttons
            if index == 0:
                self.prev_button.setDisabled(True)
                # self.start_buffer_layout.setContentsMargins(0,0,0,0)
            else:
                # self.start_buffer_layout.setContentsMargins(3,0,3,0)
                self._assign_click(self.prev_button, index - 1)
                self.prev_button.setDisabled(False)

            if index == end_page:
                self.next_button.setDisabled(True)
                # self.end_buffer_layout.setContentsMargins(0,0,0,0)
            else:
                # self.end_buffer_layout.setContentsMargins(3,0,3,0)
                self._assign_click(self.next_button, index + 1)
                self.next_button.setDisabled(False)

            # Set Ellipses Sizes
            # I do not know where these magic values were derived from, but
            # this is better than the chain elif's that were here before
            if 8 <= page_count <= 11:
                end_scale = max(1, page_count - index - 6)
                srt_scale = max(1, index - 5)
            elif page_count > 11:
                end_scale = max(1, 7 - index)
                srt_scale = max(1, (7 - (end_page - index)))

            if page_count >= 8:
                end_size = self.button_size.width() * end_scale + (3 * (end_scale - 1))
                srt_size = self.button_size.width() * srt_scale + (3 * (srt_scale - 1))
                self.end_ellipses.setMinimumWidth(end_size)
                self.end_ellipses.setMaximumWidth(end_size)
                self.start_ellipses.setMinimumWidth(srt_size)
                self.start_ellipses.setMaximumWidth(srt_size)

            # Enable/Disable Ellipses
            # if index <= max(self.buffer_page_count, 5)+1:
            if index <= self.buffer_page_count + 1:
                self.start_ellipses.setHidden(True)
                # self.start_button.setHidden(True)
            else:
                self.start_ellipses.setHidden(False)
                # self.start_button.setHidden(False)
                # self.start_button.setText('1')
                self._assign_click(self.start_button, 0)
            # if index >=(page_count-max(self.buffer_page_count, 5)-2):
            if index >= (page_count - self.buffer_page_count - 2):
                self.end_ellipses.setHidden(True)
                # self.end_button.setHidden(True)
            else:
                self.end_ellipses.setHidden(False)
                # self.end_button.setHidden(False)
                # self.end_button.setText(str(page_count))
                # self.assign_click(self.end_button, page_count-1)

            # Hide/Unhide Start+End Buttons
            if index != 0:
                self.start_button.setText("1")
                self._assign_click(self.start_button, 0)
                self.start_button.setHidden(False)
                # self.start_buffer_layout.setContentsMargins(3,0,0,0)
            else:
                self.start_button.setHidden(True)
                # self.start_buffer_layout.setContentsMargins(0,0,0,0)
            if index != page_count - 1:
                self.end_button.setText(str(page_count))
                self._assign_click(self.end_button, page_count - 1)
                self.end_button.setHidden(False)
                # self.end_buffer_layout.setContentsMargins(0,0,3,0)
            else:
                self.end_button.setHidden(True)
                # self.end_buffer_layout.setContentsMargins(0,0,0,0)

            if index == 0 or index == 1:
                self.start_buffer_container.setHidden(True)
            else:
                self.start_buffer_container.setHidden(False)

            if index == page_count - 1 or index == page_count - 2:
                self.end_buffer_container.setHidden(True)
            else:
                self.end_buffer_container.setHidden(False)

            # for i in range(0, self.buffer_page_count):
            # 	self.start_buffer_layout.itemAt(i).widget().setHidden(True)

            # Current Field and Buffer Pages
            sbc = 0
            # for i in range(0, max(self.buffer_page_count*2, 11)):
            for i in range(0, page_count):
                # for j in range(0, self.buffer_page_count+1):
                # 	self.start_buffer_layout.itemAt(j).widget().setHidden(True)
                # if i == 1:
                # 	self.start_buffer_layout.itemAt(i).widget().setHidden(True)
                # elif i == page_count-2:
                # 	self.end_buffer_layout.itemAt(i).widget().setHidden(True)

                # Set Field
                if i == index:
                    # print(f'Current Index: {i}')
                    if self.start_buffer_layout.itemAt(i):
                        self.start_buffer_layout.itemAt(i).widget().setHidden(True)
                    if self.end_buffer_layout.itemAt(i):
                        self.end_buffer_layout.itemAt(i).widget().setHidden(True)
                    sbc += 1
                    self.current_page_field.setText((str(i + 1)))
                # elif index == page_count-1:
                # 	self.start_button.setText(str(page_count))

                start_offset = max(0, (index - 4) - 4)
                end_offset = min(page_count - 1, (index + 4) - 4)
                if i < index:
                    # if i != 0 and ((i-self.buffer_page_count) >= 0 or i <= self.buffer_page_count):
                    if (i != 0) and i >= index - 4:
                        # print(f'     Start i: {i}')
                        # print(f'Start Offset: {start_offset}')
                        # print(f' Requested i: {i-start_offset}')
                        # print(f'Setting Text "{str(i+1)}" for Local Start i:{i-start_offset}, Global i:{i}')
                        self.start_buffer_layout.itemAt(
                            i - start_offset
                        ).widget().setHidden(False)
                        self.start_buffer_layout.itemAt(
                            i - start_offset
                        ).widget().setText(str(i + 1))  # type: ignore
                        self._assign_click(
                            self.start_buffer_layout.itemAt(i - start_offset).widget(),  # type: ignore
                            i,
                        )
                        sbc += 1
                    else:
                        if self.start_buffer_layout.itemAt(i):
                            # print(f'Removing S-Start {i}')
                            self.start_buffer_layout.itemAt(i).widget().setHidden(True)
                        if self.end_buffer_layout.itemAt(i):
                            # print(f'Removing S-End {i}')
                            self.end_buffer_layout.itemAt(i).widget().setHidden(True)
                elif i > index:
                    # if i != page_count-1:
                    if i != page_count - 1 and i <= index + 4:
                        # print(f'End Buffer: {i}')
                        # print(f'      End i: {i}')
                        # print(f' End Offset: {end_offset}')
                        # print(f'Requested i: {i-end_offset}')
                        # print(f'Requested i: {end_offset-sbc-i}')
                        # if self.start_buffer_layout.itemAt(i):
                        # 	self.start_buffer_layout.itemAt(i).widget().setHidden(True)
                        # print(f'Setting Text "{str(i+1)}" for Local End i:{i-end_offset}, Global i:{i}')
                        self.end_buffer_layout.itemAt(
                            i - end_offset
                        ).widget().setHidden(False)
                        self.end_buffer_layout.itemAt(i - end_offset).widget().setText(  # type: ignore
                            str(i + 1)
                        )
                        self._assign_click(
                            self.end_buffer_layout.itemAt(i - end_offset).widget(),  # type: ignore
                            i,
                        )
                    else:
                        # if self.start_buffer_layout.itemAt(i-1):
                        # 	print(f'Removing E-Start {i-1}')
                        # 	self.start_buffer_layout.itemAt(i-1).widget().setHidden(True)
                        # if self.start_buffer_layout.itemAt(i-start_offset):
                        # 	print(f'Removing E-Start Offset {i-end_offset}')
                        # 	self.start_buffer_layout.itemAt(i-end_offset).widget().setHidden(True)

                        if self.end_buffer_layout.itemAt(i):
                            # print(f'Removing E-End {i}')
                            self.end_buffer_layout.itemAt(i).widget().setHidden(True)
                        for j in range(0, self.buffer_page_count):
                            if self.end_buffer_layout.itemAt(i - end_offset + j):
                                # print(f'Removing E-End-Offset {i-end_offset+j}')
                                self.end_buffer_layout.itemAt(
                                    i - end_offset + j
                                ).widget().setHidden(True)

                    # if self.end_buffer_layout.itemAt(i+1):
                    # 	print(f'Removing T-End {i+1}')
                    # 	self.end_buffer_layout.itemAt(i+1).widget().setHidden(True)

                    if self.start_buffer_layout.itemAt(i - 1):
                        # print(f'Removing T-Start {i-1}')
                        self.start_buffer_layout.itemAt(i - 1).widget().setHidden(True)

                # if index == 0 or index == 1:
                # 	print(f'Removing Start i: {i}')
                # 	if self.start_buffer_layout.itemAt(i):
                # 		self.start_buffer_layout.itemAt(i).widget().setHidden(True)

                # elif index == page_count-1 or index == page_count-2 or index == page_count-3 or index == page_count-4:
                # 	print(f' Removing End i: {i}')
                # 	if self.end_buffer_layout.itemAt(i):
                # 		self.end_buffer_layout.itemAt(i).widget().setHidden(True)

                # else:
                # 	print(f'Truncate: {i}')
                # 	if self.start_buffer_layout.itemAt(i):
                # 		self.start_buffer_layout.itemAt(i).widget().setHidden(True)
                # 	if self.end_buffer_layout.itemAt(i):
                # 		self.end_buffer_layout.itemAt(i).widget().setHidden(True)

                # if i < self.buffer_page_count:
                # 	print(f'start {i}')
                # 	if i == 0:
                # 		self.start_buffer_layout.itemAt(i).widget().setHidden(True)
                # 		self.current_page_field.setText((str(i+1)))
                # 	else:
                # 		self.start_buffer_layout.itemAt(i).widget().setHidden(False)
                # 		self.start_buffer_layout.itemAt(i).widget().setText(str(i+1))
                # elif i >= self.buffer_page_count and i < count:
                # 	print(f'end {i}')
                # 	self.end_buffer_layout.itemAt(i-self.buffer_page_count).widget().setHidden(False)
                # 	self.end_buffer_layout.itemAt(i-self.buffer_page_count).widget().setText(str(i+1))
                # else:
                # 	self.end_buffer_layout.itemAt(i-self.buffer_page_count).widget().setHidden(True)

            self.setHidden(False)
        # elif page_count >= 7:
        # 	# Show everything, except truncate the buffers as needed.
        # 	# [<] [1]...[3] [4] [5]...[7] [>]
        # 	self.start_button.setHidden(False)
        # 	self.start_ellipses.setHidden(False)
        # 	self.end_ellipses.setHidden(False)
        # 	self.end_button.setHidden(False)

        # 	if index == 0:
        # 		self.prev_button.setDisabled(True)
        # 		self.start_buffer_layout.setContentsMargins(0,0,3,0)
        # 	else:
        # 		self.start_buffer_layout.setContentsMargins(3,0,3,0)
        # 		self.assign_click(self.prev_button, index-1)
        # 		self.prev_button.setDisabled(False)

        # 	if index == page_count-1:
        # 		self.next_button.setDisabled(True)
        # 		self.end_buffer_layout.setContentsMargins(3,0,0,0)
        # 	else:
        # 		self.end_buffer_layout.setContentsMargins(3,0,3,0)
        # 		self.assign_click(self.next_button, index+1)
        # 		self.next_button.setDisabled(False)

        # 	self.start_button.setText('1')
        # 	self.assign_click(self.start_button, 0)
        # 	self.end_button.setText(str(page_count))
        # 	self.assign_click(self.end_button, page_count-1)

        # 	self.setHidden(False)

        self.validator.setTop(page_count)
        # if self.current_page_index != index:
        if emit:
            logger.info(f"[PAGINATION] Emitting {index}")
            self.index.emit(index)
        self.current_page_index = index
        self.page_count = page_count

    def _goto_page(self, index: int):
        # print(f'GOTO PAGE: {index}')
        self.update_buttons(self.page_count, index)

    def _assign_click(self, button: QPushButton, index):
        try:
            button.clicked.disconnect()
        except RuntimeError:
            pass
        button.clicked.connect(lambda checked=False, i=index: self._goto_page(i))

    def _populate_buffer_buttons(self):
        for i in range(max(self.buffer_page_count * 2, 5)):
            button = QPushButton()
            button.setMinimumSize(self.button_size)
            button.setMaximumSize(self.button_size)
            button.setHidden(True)
            # button.setMaximumHeight(self.button_size.height())
            self.start_buffer_layout.addWidget(button)

        for i in range(max(self.buffer_page_count * 2, 5)):
            button = QPushButton()
            button.setMinimumSize(self.button_size)
            button.setMaximumSize(self.button_size)
            button.setHidden(True)
            # button.setMaximumHeight(self.button_size.height())
            self.end_buffer_layout.addWidget(button)


class Validator(QIntValidator):
    def __init__(self, bottom: int, top: int, parent=None) -> None:
        super().__init__(bottom, top, parent)

    def fixup(self, input: str) -> str:
        # print(input)
        input = input.strip("0")
        logger.info(input)
        return super().fixup(str(self.top()) if input else "1")
