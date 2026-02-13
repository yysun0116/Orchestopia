import re
import builtins
from typing import Dict, Any, Tuple

def get_namespace_and_key(key_with_namespace: str) -> Tuple[str, str]:
    pattern = r"@(\w+):(\w+)"
    try:
        match = re.match(pattern, key_with_namespace)
        if match:
            namespace, key = match.groups()
            return namespace, key
    except ValueError:
        raise ValueError(f"Invalid reference format: {key_with_namespace}")

def resolve_basemodel_type(type_str: str, created_models: Dict[str, type]) -> Any:
    try:
        # for created BaseModel, return directly
        if type_str in created_models:
            return created_models[type_str]
        # 其他一般型別（含 Optional[str]）透過 eval 處理
        cls =  eval(
            type_str, 
            {
                **vars(__import__("typing")), 
                **vars(builtins), 
                **created_models
            }
        )
        return cls
    except Exception as e:
        raise ValueError(f"Unable to resolve type: {type_str}") from e
