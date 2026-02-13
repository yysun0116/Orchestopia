from pydantic import BaseModel, Field
from typing import Dict, Any, List
from pathlib import Path
import yaml


class FormatFieldSpec(BaseModel):
    type: str
    default: Any = Field(default_factory=lambda: ...)

class FormatConfig(BaseModel):
    display_name: str
    fields: Dict[str, FormatFieldSpec]

class FormatConfigLoader(BaseModel):
    @classmethod
    def load_from_yaml(
        cls, config_path: str = f"{Path(__file__).resolve().parent.parent.parent}/config"
    ) -> List[FormatConfig]:
        instance = cls()
        # read yaml
        with open(f"{config_path}/format.yaml") as f:
            raw_config = yaml.safe_load(f)
        # convert into FormatConfig
        return instance.load_from_dict(raw_config)

    def load_from_dict(self, raw_config: dict) -> List[FormatConfig]:
        return [
            FormatConfig(**item)
            for item in raw_config.get("formats", [])
        ]