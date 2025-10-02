import builtins
from typing import Dict, Any
from pydantic import BaseModel, create_model


def resolve_basemodel_type(type_str: str, created_models: dict[str, type]) -> Any:
    try:
        # 如果是已建立的 model 名稱，直接回傳
        if type_str in created_models:
            return created_models[type_str]
        # 其他一般型別（含 Optional[str]）透過 eval 處理
        return eval(
            type_str, {**vars(__import__("typing")), **vars(builtins), **created_models}
        )
    except Exception as e:
        raise ValueError(f"Unable to resolve type: {type_str}") from e


def build_formats(
    structured_output_config: Dict[str, Any],
) -> Dict[str, type[BaseModel]]:
    output_formats: dict[str, type[BaseModel]] = {}

    for fields in structured_output_config["formats"]:
        format_name = fields.pop("display_name", None)
        if not format_name:
            raise ValueError("Each format must have a `display_name` field...")

        model_fields = {}
        for field_name, value in fields.items():
            if isinstance(value, dict):
                field_type_str = value["type"]
                default = value.get("default", ...)
            else:
                field_type_str = value
                default = ...
            resolved_type = resolve_basemodel_type(field_type_str, output_formats)
            model_fields[field_name] = (resolved_type, default)
        # Create and save the BaseModel
        output_formats[format_name] = create_model(format_name, **model_fields)
    return output_formats
