"""提取后的梅花易数预测模块总入口。"""

from importlib import import_module
import sys
from typing import List

_core = import_module(".meihuayishu", __name__)

__all__: List[str] = []
if hasattr(_core, "__all__"):
    __all__.extend(_core.__all__)  # type: ignore[arg-type]
    for name in _core.__all__:  # type: ignore[attr-defined]
        globals()[name] = getattr(_core, name)

for _submodule in ("iching", "config", "data"):
    module = import_module(f".meihuayishu.{_submodule}", __name__)
    sys.modules[f"{__name__}.{_submodule}"] = module
    globals()[_submodule] = module

__all__.extend(["iching", "config", "data"])
