import logging
import sys

from auric.container import build


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    try:
        app = build()
        app.start()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
