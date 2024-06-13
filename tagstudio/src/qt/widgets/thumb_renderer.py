# Copyright (C) 2024 Travis Abendshien (CyanVoxel).
# Licensed under the GPL-3.0 License.
# Created for TagStudio: https://github.com/CyanVoxel/TagStudio


import logging
import math
import cv2
import rawpy
import numpy
from pillow_heif import register_heif_opener, register_avif_opener
from PIL import (
    Image,
    UnidentifiedImageError,
    ImageQt,
    ImageDraw,
    ImageFont,
    ImageOps,
    ImageFile,
)
from io import BytesIO
from pathlib import Path
from PIL.Image import DecompressionBombError
from pydub import AudioSegment, exceptions
from mutagen import id3, flac, mp4
from PySide6.QtCore import QObject, Signal, QSize
from PySide6.QtGui import QPixmap
from src.qt.helpers.gradient import four_corner_gradient_background
from src.core.constants import (
    AUDIO_TYPES,
    PLAINTEXT_TYPES,
    VIDEO_TYPES,
    IMAGE_TYPES,
    RAW_IMAGE_TYPES,
)
from src.core.utils.encoding import detect_char_encoding
from src.qt.helpers.file_tester import is_readable_video

ImageFile.LOAD_TRUNCATED_IMAGES = True

ERROR = "[ERROR]"
WARNING = "[WARNING]"
INFO = "[INFO]"

logging.basicConfig(format="%(message)s", level=logging.INFO)
register_heif_opener()
register_avif_opener()


class ThumbRenderer(QObject):
    # finished = Signal()
    updated = Signal(float, QPixmap, QSize, str)
    updated_ratio = Signal(float)
    # updatedImage = Signal(QPixmap)
    # updatedSize = Signal(QSize)

    thumb_mask_512: Image.Image = Image.open(
        Path(__file__).parents[3] / "resources/qt/images/thumb_mask_512.png"
    )
    thumb_mask_512.load()

    thumb_mask_hl_512: Image.Image = Image.open(
        Path(__file__).parents[3] / "resources/qt/images/thumb_mask_hl_512.png"
    )
    thumb_mask_hl_512.load()

    thumb_loading_512: Image.Image = Image.open(
        Path(__file__).parents[3] / "resources/qt/images/thumb_loading_512.png"
    )
    thumb_loading_512.load()

    thumb_broken_512: Image.Image = Image.open(
        Path(__file__).parents[3] / "resources/qt/images/thumb_broken_512.png"
    )
    thumb_broken_512.load()

    thumb_file_default_512: Image.Image = Image.open(
        Path(__file__).parents[3] / "resources/qt/images/thumb_file_default_512.png"
    )
    thumb_file_default_512.load()

    # thumb_debug: Image.Image = Image.open(Path(
    # 	f'{Path(__file__).parents[2]}/resources/qt/images/temp.jpg'))
    # thumb_debug.load()

    # TODO: Make dynamic font sized given different pixel ratios
    font_pixel_ratio: float = 1
    ext_font = ImageFont.truetype(
        Path(__file__).parents[3] / "resources/qt/fonts/Oxanium-Bold.ttf",
        math.floor(12 * font_pixel_ratio),
    )

    def render(
        self,
        timestamp: float,
        filepath: str | Path,
        base_size: tuple[int, int],
        pixel_ratio: float,
        is_loading=False,
        gradient=False,
        update_on_ratio_change=False,
    ):
        """Internal renderer. Renders an entry/element thumbnail for the GUI."""
        image: Image.Image = None
        pixmap: QPixmap = None
        final: Image.Image = None
        _filepath: Path = Path(filepath)
        resampling_method = Image.Resampling.BILINEAR
        if ThumbRenderer.font_pixel_ratio != pixel_ratio:
            ThumbRenderer.font_pixel_ratio = pixel_ratio
            ThumbRenderer.ext_font = ImageFont.truetype(
                Path(__file__).parents[3] / "resources/qt/fonts/Oxanium-Bold.ttf",
                math.floor(12 * ThumbRenderer.font_pixel_ratio),
            )

        adj_size = math.ceil(max(base_size[0], base_size[1]) * pixel_ratio)
        if is_loading:
            final = ThumbRenderer.thumb_loading_512.resize(
                (adj_size, adj_size), resample=Image.Resampling.BILINEAR
            )
            qim = ImageQt.ImageQt(final)
            pixmap = QPixmap.fromImage(qim)
            pixmap.setDevicePixelRatio(pixel_ratio)
            if update_on_ratio_change:
                self.updated_ratio.emit(1)
        elif _filepath:
            try:
                # Images =======================================================
                if _filepath.suffix.lower() in IMAGE_TYPES:
                    try:
                        image = Image.open(_filepath)
                        if image.mode != "RGB" and image.mode != "RGBA":
                            image = image.convert(mode="RGBA")
                        if image.mode == "RGBA":
                            new_bg = Image.new("RGB", image.size, color="#1e1e1e")
                            new_bg.paste(image, mask=image.getchannel(3))
                            image = new_bg

                        image = ImageOps.exif_transpose(image)
                    except DecompressionBombError as e:
                        logging.info(
                            f"[ThumbRenderer]{WARNING} Couldn't Render thumbnail for {_filepath.name} ({type(e).__name__})"
                        )

                elif _filepath.suffix.lower() in RAW_IMAGE_TYPES:
                    try:
                        with rawpy.imread(str(_filepath)) as raw:
                            rgb = raw.postprocess()
                            image = Image.frombytes(
                                "RGB",
                                (rgb.shape[1], rgb.shape[0]),
                                rgb,
                                decoder_name="raw",
                            )
                    except DecompressionBombError as e:
                        logging.info(
                            f"[ThumbRenderer]{WARNING} Couldn't Render thumbnail for {_filepath.name} ({type(e).__name__})"
                        )
                    except (
                        rawpy._rawpy.LibRawIOError,
                        rawpy._rawpy.LibRawFileUnsupportedError,
                    ) as e:
                        logging.info(
                            f"[ThumbRenderer]{ERROR} Couldn't Render thumbnail for raw image {_filepath.name} ({type(e).__name__})"
                        )

                # Videos =======================================================
                elif _filepath.suffix.lower() in VIDEO_TYPES:
                    if is_readable_video(_filepath):
                        video = cv2.VideoCapture(str(_filepath), cv2.CAP_FFMPEG)
                        video.set(
                            cv2.CAP_PROP_POS_FRAMES,
                            (video.get(cv2.CAP_PROP_FRAME_COUNT) // 2),
                        )
                        success, frame = video.read()
                        if not success:
                            # Depending on the video format, compression, and frame
                            # count, seeking halfway does not work and the thumb
                            # must be pulled from the earliest available frame.
                            video.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            success, frame = video.read()
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        image = Image.fromarray(frame)
                    else:
                        image = self.thumb_file_default_512

                # Plain Text ===================================================
                elif _filepath.suffix.lower() in PLAINTEXT_TYPES:
                    encoding = detect_char_encoding(_filepath)
                    with open(_filepath, "r", encoding=encoding) as text_file:
                        text = text_file.read(256)
                    bg = Image.new("RGB", (256, 256), color="#1e1e1e")
                    draw = ImageDraw.Draw(bg)
                    draw.text((16, 16), text, file=(255, 255, 255))
                    image = bg
                # Audio
                elif _filepath.suffix.lower() in AUDIO_TYPES:
                    try:
                        artwork = None
                        if _filepath.suffix.lower() in [".mp3"]:
                            id3_tags: id3.ID3 = id3.ID3(_filepath)
                            id3_covers: list = id3_tags.getall("APIC")
                            if id3_covers:
                                artwork = Image.open(BytesIO(id3_covers[0].data))
                        elif _filepath.suffix.lower() in [".flac"]:
                            flac_tags: flac.FLAC = flac.FLAC(_filepath)
                            flac_covers: list = flac_tags.pictures
                            if flac_covers:
                                artwork = Image.open(BytesIO(flac_covers[0].data))
                        elif _filepath.suffix.lower() in [".mp4", ".m4a", ".aac"]:
                            mp4_tags: mp4.MP4 = mp4.MP4(_filepath)
                            mp4_covers: list = mp4_tags.get("covr")
                            if mp4_covers:
                                artwork = Image.open(BytesIO(mp4_covers[0]))
                        if artwork:
                            image = artwork
                    except (
                        mp4.MP4MetadataError,
                        mp4.MP4StreamInfoError,
                        id3.ID3NoHeaderError,
                    ) as e:
                        logging.error(
                            f"[ThumbRenderer]{ERROR}: Couldn't read album artwork for {_filepath.name} ({type(e).__name__})"
                        )
                    if image is None:
                        try:
                            audio: AudioSegment = AudioSegment.from_file(
                                _filepath, _filepath.suffix.lower()[1:]
                            )
                            data = numpy.fromstring(audio._data, numpy.int16)  # type: ignore
                            data_indices = numpy.linspace(1, len(data), num=adj_size)

                            BARS = adj_size // 5
                            BAR_MARGIN = 4
                            BAR_HEIGHT = adj_size - (adj_size // BAR_MARGIN)
                            LINE_WIDTH = 6

                            length = len(data_indices)
                            RATIO = length / BARS

                            count = 0
                            maximum_item = 0
                            max_array = []
                            highest_line = 0

                            for i in range(1, len(data_indices)):
                                d = data[math.ceil(data_indices[i]) - 1]
                                if count < RATIO:
                                    count = count + 1
                                    if abs(d) > maximum_item:
                                        maximum_item = abs(d)
                                else:
                                    max_array.append(maximum_item)

                                    if maximum_item > highest_line:
                                        highest_line = maximum_item

                                    maximum_item = 0
                                    count = 1

                            line_ratio = max(highest_line / BAR_HEIGHT, 1)

                            image = Image.new(
                                "RGB", (adj_size, adj_size), color="#1e1e1e"
                            )
                            draw = ImageDraw.Draw(image)

                            current_x = 1
                            for item in max_array:
                                item_height = item / line_ratio

                                current_y = (
                                    BAR_HEIGHT - item_height + (adj_size // BAR_MARGIN)
                                ) / 2
                                draw.line(
                                    (
                                        current_x,
                                        current_y,
                                        current_x,
                                        current_y + item_height,
                                    ),
                                    fill=(169, 171, 172),
                                    width=4,
                                    joint="curve",
                                )

                                current_x = current_x + LINE_WIDTH
                        except exceptions.CouldntDecodeError as e:
                            logging.error(
                                f"[ThumbRenderer]{ERROR}: Couldn't render waveform for {_filepath.name} ({type(e).__name__})"
                            )

                # 3D ===========================================================
                # elif extension == 'stl':
                # 	# Create a new plot
                # 	matplotlib.use('agg')
                # 	figure = plt.figure()
                # 	axes = figure.add_subplot(projection='3d')

                # 	# Load the STL files and add the vectors to the plot
                # 	your_mesh = mesh.Mesh.from_file(_filepath)

                # 	poly_collection = mplot3d.art3d.Poly3DCollection(your_mesh.vectors)
                # 	poly_collection.set_color((0,0,1))  # play with color
                # 	scale = your_mesh.points.flatten()
                # 	axes.auto_scale_xyz(scale, scale, scale)
                # 	axes.add_collection3d(poly_collection)
                # 	# plt.show()
                # 	img_buf = io.BytesIO()
                # 	plt.savefig(img_buf, format='png')
                # 	image = Image.open(img_buf)
                # No Rendered Thumbnail ========================================
                else:
                    image = ThumbRenderer.thumb_file_default_512.resize(
                        (adj_size, adj_size), resample=Image.Resampling.BILINEAR
                    )

                if not image:
                    raise UnidentifiedImageError

                orig_x, orig_y = image.size
                new_x, new_y = (adj_size, adj_size)

                if orig_x > orig_y:
                    new_x = adj_size
                    new_y = math.ceil(adj_size * (orig_y / orig_x))
                elif orig_y > orig_x:
                    new_y = adj_size
                    new_x = math.ceil(adj_size * (orig_x / orig_y))

                if update_on_ratio_change:
                    self.updated_ratio.emit(new_x / new_y)

                resampling_method = (
                    Image.Resampling.NEAREST
                    if max(image.size[0], image.size[1])
                    < max(base_size[0], base_size[1])
                    else Image.Resampling.BILINEAR
                )
                image = image.resize((new_x, new_y), resample=resampling_method)
                if gradient:
                    mask: Image.Image = ThumbRenderer.thumb_mask_512.resize(
                        (adj_size, adj_size), resample=Image.Resampling.BILINEAR
                    ).getchannel(3)
                    hl: Image.Image = ThumbRenderer.thumb_mask_hl_512.resize(
                        (adj_size, adj_size), resample=Image.Resampling.BILINEAR
                    )
                    final = four_corner_gradient_background(image, adj_size, mask, hl)
                else:
                    scalar = 4
                    rec: Image.Image = Image.new(
                        "RGB",
                        tuple([d * scalar for d in image.size]),  # type: ignore
                        "black",
                    )
                    draw = ImageDraw.Draw(rec)
                    draw.rounded_rectangle(
                        (0, 0) + rec.size,
                        (base_size[0] // 32) * scalar * pixel_ratio,
                        fill="red",
                    )
                    rec = rec.resize(
                        tuple([d // scalar for d in rec.size]),
                        resample=Image.Resampling.BILINEAR,
                    )
                    final = Image.new("RGBA", image.size, (0, 0, 0, 0))
                    final.paste(image, mask=rec.getchannel(0))
            except (
                UnidentifiedImageError,
                FileNotFoundError,
                cv2.error,
                DecompressionBombError,
                UnicodeDecodeError,
            ) as e:
                if e is not UnicodeDecodeError:
                    logging.info(
                        f"[ThumbRenderer]{ERROR}: Couldn't render thumbnail for {_filepath.name} ({type(e).__name__})"
                    )
                if update_on_ratio_change:
                    self.updated_ratio.emit(1)
                final = ThumbRenderer.thumb_broken_512.resize(
                    (adj_size, adj_size), resample=resampling_method
                )
            qim = ImageQt.ImageQt(final)
            if image:
                image.close()
            pixmap = QPixmap.fromImage(qim)
            pixmap.setDevicePixelRatio(pixel_ratio)

        if pixmap:
            self.updated.emit(
                timestamp,
                pixmap,
                QSize(
                    math.ceil(adj_size / pixel_ratio),
                    math.ceil(final.size[1] / pixel_ratio),
                ),
                _filepath.suffix.lower(),
            )

        else:
            self.updated.emit(
                timestamp, QPixmap(), QSize(*base_size), _filepath.suffix.lower()
            )
