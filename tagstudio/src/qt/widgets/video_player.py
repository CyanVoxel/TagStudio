import logging
import typing

# os.environ["QT_MEDIA_BACKEND"] = "ffmpeg"

from PySide6.QtCore import (
    Qt,
    QSize,
    QTimer,
    QVariantAnimation,
    QUrl,
    QObject,
    QEvent,
    QRectF,
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtGui import (
    QPen,
    QColor,
    QBrush,
    QResizeEvent,
    QWheelEvent,
    QAction,
    QRegion,
    QBitmap,
)
from PySide6.QtSvgWidgets import QSvgWidget
from PIL import Image
from src.qt.helpers.file_opener import FileOpenerHelper

from PIL import ImageDraw
from src.core.enums import SettingItems

if typing.TYPE_CHECKING:
    from src.qt.ts_qt import QtDriver


class VideoPlayer(QGraphicsView):
    """A simple video player for the TagStudio application."""

    resolution = QSize(1280, 720)
    hover_fix_timer = QTimer()
    video_preview = None
    play_pause = None
    mute_button = None
    content_visible = False
    filepath = None

    def __init__(self, driver: "QtDriver") -> None:
        # Set up the base class.
        super().__init__()
        self.driver = driver
        self.animation = QVariantAnimation(self)
        self.animation.valueChanged.connect(
            lambda value: self.setTintTransparency(value)
        )
        self.hover_fix_timer.timeout.connect(lambda: self.checkIfStillHovered())
        self.hover_fix_timer.setSingleShot(True)
        # Set up the video player.
        self.installEventFilter(self)
        self.setScene(QGraphicsScene(self))
        self.player = QMediaPlayer(self)
        self.player.mediaStatusChanged.connect(
            lambda: self.checkMediaStatus(self.player.mediaStatus())
        )
        self.video_preview = VideoPreview()
        self.player.setVideoOutput(self.video_preview)
        self.video_preview.setAcceptHoverEvents(True)
        self.video_preview.setAcceptedMouseButtons(Qt.MouseButton.RightButton)
        self.video_preview.installEventFilter(self)
        self.player.setAudioOutput(
            QAudioOutput(QMediaDevices().defaultAudioOutput(), self.player)
        )
        self.player.audioOutput().setMuted(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scene().addItem(self.video_preview)
        self.video_preview.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        # Set up the video tint.
        self.video_tint = self.scene().addRect(
            0,
            0,
            self.video_preview.size().width(),
            self.video_preview.size().height(),
            QPen(QColor(0, 0, 0, 0)),
            QBrush(QColor(0, 0, 0, 0)),
        )
        # self.video_tint.setParentItem(self.video_preview)
        # self.album_art = QGraphicsPixmapItem(self.video_preview)
        # self.scene().addItem(self.album_art)
        # self.album_art.setPixmap(
        #     QPixmap("./tagstudio/resources/qt/images/thumb_file_default_512.png")
        # )
        # self.album_art.setOpacity(0.0)
        # Set up the buttons.
        self.play_pause = QSvgWidget("./tagstudio/resources/pause.svg")
        self.play_pause.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.play_pause.setMouseTracking(True)
        self.play_pause.installEventFilter(self)
        self.scene().addWidget(self.play_pause)
        self.play_pause.resize(100, 100)
        self.play_pause.move(
            int(self.width() / 2 - self.play_pause.size().width() / 2),
            int(self.height() / 2 - self.play_pause.size().height() / 2),
        )
        self.play_pause.hide()

        self.mute_button = QSvgWidget("./tagstudio/resources/volume_muted.svg")
        self.mute_button.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.mute_button.setMouseTracking(True)
        self.mute_button.installEventFilter(self)
        self.scene().addWidget(self.mute_button)
        self.mute_button.resize(40, 40)
        self.mute_button.move(
            int(self.width() - self.mute_button.size().width() / 2),
            int(self.height() - self.mute_button.size().height() / 2),
        )
        self.mute_button.hide()
        # self.fullscreen_button = QSvgWidget('./tagstudio/resources/pause.svg', self)
        # self.fullscreen_button.setMouseTracking(True)
        # self.fullscreen_button.installEventFilter(self)
        # self.scene().addWidget(self.fullscreen_button)
        # self.fullscreen_button.resize(40, 40)
        # self.fullscreen_button.move(self.fullscreen_button.size().width()/2, self.height() - self.fullscreen_button.size().height()/2)
        # self.fullscreen_button.hide()

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        self.opener = FileOpenerHelper(filepath=self.filepath)
        autoplay_action = QAction("Autoplay", self)
        autoplay_action.setCheckable(True)
        self.addAction(autoplay_action)
        autoplay_action.setChecked(
            self.driver.settings.value(SettingItems.AUTOPLAY, True, bool)  # type: ignore
        )
        autoplay_action.triggered.connect(lambda: self.toggleAutoplay())
        self.autoplay = autoplay_action

        open_file_action = QAction("Open file", self)
        open_file_action.triggered.connect(self.opener.open_file)
        open_explorer_action = QAction("Open file in explorer", self)
        open_explorer_action.triggered.connect(self.opener.open_explorer)
        self.addAction(open_file_action)
        self.addAction(open_explorer_action)

    def close(self, *args, **kwargs) -> None:
        self.player.stop()
        super().close(*args, **kwargs)

    def toggleAutoplay(self) -> None:
        self.driver.settings.setValue(SettingItems.AUTOPLAY, self.autoplay.isChecked())
        self.driver.settings.sync()

    def checkMediaStatus(self, media_status: QMediaPlayer.MediaStatus) -> None:
        # logging.info(media_status)
        if media_status == QMediaPlayer.MediaStatus.EndOfMedia:
            # Switches current video to with video at filepath. Reason for this is because Pyside6 is dumb and can't handle setting a new source and freezes.
            # Even if I stop the player before switching, it breaks.
            # On the plus side, this adds infinite looping for the video preview.
            self.player.stop()
            self.player.setSource(QUrl().fromLocalFile(self.filepath))
            # logging.info(f'Set source to {self.filepath}.')
            # self.video_preview.setSize(self.resolution)
            self.player.setPosition(0)
            # logging.info(f'Set muted to true.')
            if self.autoplay.isChecked():
                # logging.info(self.driver.settings.value("autoplay_videos", True, bool))
                self.player.play()
            else:
                # logging.info("Paused")
                self.player.pause()
            self.opener.set_filepath(self.filepath)
            self.keepControlsInPlace()
        self.updateControls()

    def updateControls(self) -> None:
        if self.player.audioOutput().isMuted():
            self.mute_button.load("./tagstudio/resources/volume_muted.svg")
        else:
            self.mute_button.load("./tagstudio/resources/volume_unmuted.svg")

        if self.player.isPlaying():
            self.play_pause.load("./tagstudio/resources/pause.svg")
        else:
            self.play_pause.load("./tagstudio/resources/play.svg")

    def wheelEvent(self, event: QWheelEvent) -> None:
        return

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        # This chunk of code is for the video controls.
        if (
            obj == self.play_pause
            and event.type() == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton  # type: ignore
        ):
            if self.player.hasVideo():
                self.pauseToggle()

        if (
            obj == self.mute_button
            and event.type() == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton  # type: ignore
        ):
            if self.player.hasAudio():
                self.muteToggle()

        if (
            obj == self.video_preview
            and event.type() == QEvent.Type.GraphicsSceneHoverEnter
            or event.type() == QEvent.Type.HoverEnter
        ):
            if self.video_preview.isUnderMouse():
                self.underMouse()
                self.hover_fix_timer.start(10)
        elif (
            obj == self.video_preview
            and event.type() == QEvent.Type.GraphicsSceneHoverLeave
            or event.type() == QEvent.Type.HoverLeave
        ):
            if not self.video_preview.isUnderMouse():
                self.hover_fix_timer.stop()
                self.releaseMouse()
        return super().eventFilter(obj, event)

    def checkIfStillHovered(self) -> None:
        # Yet again, Pyside6 is dumb. I don't know why, but the HoverLeave event is not triggered sometimes and does not hide the controls.
        # So, this is a workaround. This is called by a QTimer every 10ms to check if the mouse is still in the video preview.
        if not self.video_preview.isUnderMouse():
            self.releaseMouse()
        else:
            self.hover_fix_timer.start(10)

    def setTintTransparency(self, value) -> None:
        self.video_tint.setBrush(QBrush(QColor(0, 0, 0, value)))

    def underMouse(self) -> bool:
        # logging.info("under mouse")
        self.animation.setStartValue(self.video_tint.brush().color().alpha())
        self.animation.setEndValue(100)
        self.animation.setDuration(500)
        self.animation.start()
        self.play_pause.show()
        self.mute_button.show()
        # self.fullscreen_button.show()
        self.keepControlsInPlace()
        self.updateControls()
        # rcontent = self.contentsRect()
        # self.setSceneRect(0, 0, rcontent.width(), rcontent.height())
        return super().underMouse()

    def releaseMouse(self) -> None:
        # logging.info("release mouse")
        self.animation.setStartValue(self.video_tint.brush().color().alpha())
        self.animation.setEndValue(0)
        self.animation.setDuration(500)
        self.animation.start()
        self.play_pause.hide()
        self.mute_button.hide()
        # self.fullscreen_button.hide()
        return super().releaseMouse()

    def resetControlsToDefault(self) -> None:
        # Resets the video controls to their default state.
        self.play_pause.load("./tagstudio/resources/pause.svg")
        self.mute_button.load("./tagstudio/resources/volume_muted.svg")

    def pauseToggle(self) -> None:
        if self.player.isPlaying():
            self.player.pause()
            self.play_pause.load("./tagstudio/resources/play.svg")
        else:
            self.player.play()
            self.play_pause.load("./tagstudio/resources/pause.svg")

    def muteToggle(self) -> None:
        if self.player.audioOutput().isMuted():
            self.player.audioOutput().setMuted(False)
            self.mute_button.load("./tagstudio/resources/volume_unmuted.svg")
        else:
            self.player.audioOutput().setMuted(True)
            self.mute_button.load("./tagstudio/resources/volume_muted.svg")

    def play(self, filepath: str, resolution: QSize) -> None:
        # Sets the filepath and sends the current player position to the very end, so that the new video can be played.
        # self.player.audioOutput().setMuted(True)
        logging.info(f"Playing {filepath}")
        self.resolution = resolution
        self.filepath = filepath
        if self.player.isPlaying():
            self.player.setPosition(self.player.duration())
            self.player.play()
        else:
            self.checkMediaStatus(QMediaPlayer.MediaStatus.EndOfMedia)
        # logging.info(f"Successfully stopped.")

    def stop(self) -> None:
        self.filepath = None
        self.player.stop()

    def resizeVideo(self, new_size: QSize) -> None:
        # Resizes the video preview to the new size.
        self.video_preview.setSize(new_size)
        self.video_tint.setRect(
            0, 0, self.video_preview.size().width(), self.video_preview.size().height()
        )

        rcontent = self.contentsRect()
        self.centerOn(self.video_preview)
        self.roundCorners()
        self.setSceneRect(0, 0, rcontent.width(), rcontent.height())
        self.keepControlsInPlace()

    def roundCorners(self) -> None:
        width: int = int(max(self.contentsRect().size().width(), 0))
        height: int = int(max(self.contentsRect().size().height(), 0))
        mask = Image.new(
            "RGBA",
            (
                width,
                height,
            ),
            (0, 0, 0, 255),
        )
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle(
            (0, 0) + (width, height),
            radius=12,
            fill=(0, 0, 0, 0),
        )
        final_mask = mask.getchannel("A").toqpixmap()
        self.setMask(QRegion(QBitmap(final_mask)))

    def keepControlsInPlace(self) -> None:
        # Keeps the video controls in the places they should be.
        self.play_pause.move(
            int(self.width() / 2 - self.play_pause.size().width() / 2),
            int(self.height() / 2 - self.play_pause.size().height() / 2),
        )
        self.mute_button.move(
            int(self.width() - self.mute_button.size().width() - 10),
            int(self.height() - self.mute_button.size().height() - 10),
        )
        # self.fullscreen_button.move(-self.fullscreen_button.size().width()-10, self.height() - self.fullscreen_button.size().height()-10)

    def resizeEvent(self, event: QResizeEvent) -> None:
        # Keeps the video preview in the center of the screen.
        self.centerOn(self.video_preview)
        self.resizeVideo(
            QSize(
                int(self.video_preview.size().width()),
                int(self.video_preview.size().height()),
            )
        )
        return
        # return super().resizeEvent(event)\


class VideoPreview(QGraphicsVideoItem):
    def boundingRect(self):
        return QRectF(0, 0, self.size().width(), self.size().height())

    def paint(self, painter, option, widget):
        # painter.brush().setColor(QColor(0, 0, 0, 255))
        # You can set any shape you want here. RoundedRect is the standard rectangle with rounded corners
        # With 2nd and 3rd parameter you can tweak the curve until you get what you expect

        super().paint(painter, option, widget)
