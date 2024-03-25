from typing import Optional

def dict2liststr(d: dict[str, str]) -> Optional[str|list[str]]:
    if len(d.items()) == 0:
        return None
    elif len(d.items()) == 1:
        return [f"{k}={v}" for k, v in d.items()][0]
    return [f"{k}={v}" for k, v in d.items()]
