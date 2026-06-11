import logging
import logging.handlers
import sys
from pathlib import Path


def setup(log_dir: str = 'logs', level: int = logging.INFO) -> None:
    Path(log_dir).mkdir(exist_ok=True)
    fmt = logging.Formatter(
        '%(asctime)s [%(name)s] %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    root = logging.getLogger()
    root.setLevel(level)
    for h in root.handlers[:]:
        root.removeHandler(h)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    fh = logging.handlers.RotatingFileHandler(
        Path(log_dir) / 'elefrac.log',
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8',
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)
