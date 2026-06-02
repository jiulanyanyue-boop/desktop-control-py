"""支持 `python -m desktop_control_py` 启动方式。"""

from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
