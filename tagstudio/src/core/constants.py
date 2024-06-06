VERSION: str = "9.2.2"  # Major.Minor.Patch
VERSION_BRANCH: str = "Pre-Release"  # 'Alpha', 'Beta', or '' for Full Release

# The folder & file names where TagStudio keeps its data relative to a library.
TS_FOLDER_NAME: str = ".TagStudio"
BACKUP_FOLDER_NAME: str = "backups"
COLLAGE_FOLDER_NAME: str = "collages"
LIBRARY_FILENAME: str = "ts_library.json"

# TODO: Turn this whitelist into a user-configurable blacklist.
IMAGE_TYPES: list[str] = [
    ".png",
    ".jpg",
    ".jpeg",
    ".jpg_large",
    ".jpeg_large",
    ".jfif",
    ".gif",
    ".tif",
    ".tiff",
    ".heic",
    ".heif",
    ".webp",
    ".bmp",
    ".svg",
    ".avif",
    ".apng",
    ".jp2",
    ".j2k",
    ".jpg2",
]
RAW_IMAGE_TYPES: list[str] = [
    ".raw",
    ".dng",
    ".rw2",
    ".nef",
    ".arw",
    ".crw",
    ".cr2",
    ".cr3",
]
VIDEO_TYPES: list[str] = [
    ".mp4",
    ".webm",
    ".mov",
    ".hevc",
    ".mkv",
    ".avi",
    ".wmv",
    ".flv",
    ".gifv",
    ".m4p",
    ".m4v",
    ".3gp",
]
AUDIO_TYPES: list[str] = [
    ".mp3",
    ".mp4",
    ".mpeg4",
    ".m4a",
    ".aac",
    ".wav",
    ".flac",
    ".alac",
    ".wma",
    ".ogg",
    ".aiff",
]
DOC_TYPES: list[str] = [
    ".txt",
    ".rtf",
    ".md",
    ".doc",
    ".docx",
    ".pdf",
    ".tex",
    ".odt",
    ".pages",
]
PLAINTEXT_TYPES: list[str] = [
    ".txt",
    ".md",
    ".css",
    ".html",
    ".xml",
    ".json",
    ".js",
    ".ts",
    ".ini",
    ".htm",
    ".csv",
    ".php",
    ".sh",
    ".bat",
]
SPREADSHEET_TYPES: list[str] = [".csv", ".xls", ".xlsx", ".numbers", ".ods"]
PRESENTATION_TYPES: list[str] = [".ppt", ".pptx", ".key", ".odp"]
ARCHIVE_TYPES: list[str] = [
    ".zip",
    ".rar",
    ".tar",
    ".tar",
    ".gz",
    ".tgz",
    ".7z",
    ".s7z",
]
PROGRAM_TYPES: list[str] = [".exe", ".app"]
SHORTCUT_TYPES: list[str] = [".lnk", ".desktop", ".url"]

ALL_FILE_TYPES: list[str] = (
    IMAGE_TYPES
    + VIDEO_TYPES
    + AUDIO_TYPES
    + DOC_TYPES
    + SPREADSHEET_TYPES
    + PRESENTATION_TYPES
    + ARCHIVE_TYPES
    + PROGRAM_TYPES
    + SHORTCUT_TYPES
)

BOX_FIELDS = ["tag_box", "text_box"]
TEXT_FIELDS = ["text_line", "text_box"]
DATE_FIELDS = ["datetime"]

TAG_COLORS = [
    "",
    "black",
    "dark gray",
    "gray",
    "light gray",
    "white",
    "light pink",
    "pink",
    "red",
    "red orange",
    "orange",
    "yellow orange",
    "yellow",
    "lime",
    "light green",
    "mint",
    "green",
    "teal",
    "cyan",
    "light blue",
    "blue",
    "blue violet",
    "violet",
    "purple",
    "lavender",
    "berry",
    "magenta",
    "salmon",
    "auburn",
    "dark brown",
    "brown",
    "light brown",
    "blonde",
    "peach",
    "warm gray",
    "cool gray",
    "olive",
]
