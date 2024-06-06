import argparse
from functools import cache

# Building a set from tuple as it enables proper type inferencing for pyright
SUPPORTED_DRIVERS = set(
    (
        "qt",
        "cli",
    )
)


@cache
def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "--open",
        dest="open",
        type=str,
        help="Path to a TagStudio Library folder to open on start.",
    )
    parser.add_argument(
        "-o",
        dest="open",
        type=str,
        help="Path to a TagStudio Library folder to open on start.",
    )
    parser.add_argument(
        "-c",
        "--config-file",
        dest="config_file",
        type=str,
        help="Path to a TagStudio .ini or .plist config file to use.",
    )

    # parser.add_argument('--browse', dest='browse', action='store_true',
    #                     help='Jumps to entry browsing on startup.')
    # parser.add_argument('--external_preview', dest='external_preview', action='store_true',
    #                     help='Outputs current preview thumbnail to a live-updating file.')
    parser.add_argument(
        "--debug",
        dest="debug",
        action="store_true",
        help="Reveals additional internal data useful for debugging.",
    )
    parser.add_argument(
        "--ui",
        dest="ui",
        type=str,
        nargs="?",
        const="qt",
        default="qt",
        choices=SUPPORTED_DRIVERS,
        help=f"User interface option for TagStudio. Options: {', '.join(SUPPORTED_DRIVERS)}",
    )
    parser.add_argument(
        "--ci",
        action=argparse.BooleanOptionalAction,
        help="Exit the application after checking it starts without any problem. Meant for CI check.",
    )

    return parser


def parse_args() -> argparse.Namespace:
    parser = get_parser()

    # TODO: Custom namespace for proper typing
    args = parser.parse_args()

    return args
