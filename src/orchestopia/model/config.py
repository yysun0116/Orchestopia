from pydantic import BaseModel, field_validator, model_validator
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings
from pydantic_ai.models.openai import OpenAIResponsesModelSettings
from typing import Literal, Union, List
from logging import Logger
from pathlib import Path
import yaml

logger = Logger(__name__)

class ModelConfig(BaseModel):
    display_name: str = None
    model_name: str
    type: Literal['completions', 'responses']
    enabled: bool = True
    provider: OpenAIProvider = {}
    settings: Union[ModelSettings, OpenAIResponsesModelSettings] = {}

    model_config = {
        "arbitrary_types_allowed": True
    }

    @field_validator("provider", mode="before")
    def convert_provider(cls, provider_info):
        if isinstance(provider_info, dict):
            return OpenAIProvider(**provider_info)
        return provider_info
    
    @field_validator("settings", mode="after")
    def convert_settings(cls, settings, info):
        if isinstance(settings, dict):
            model_type = info.data.get("type")
            if model_type == "completions":
                return ModelSettings(**settings)
            elif model_type == "responses":
                return OpenAIResponsesModelSettings(**settings)
        return settings

    @model_validator(mode="after")
    def set_display_name(cls, model):
        # if display_name is None, set to model_name
        if not model.display_name:
            model.display_name = model.model_name
        return model

class ModelConfigLoader(BaseModel):
    @classmethod
    def load_from_yaml(
        cls, config_path: str = f"{Path(__file__).resolve().parent.parent.parent}/config"
    ) -> List[ModelConfig]:
        instance = cls()
        # read yaml
        with open(f"{config_path}/model.yaml") as f:
            raw_config = yaml.safe_load(f)
        # convert into ModelConfig
        return instance.load_from_dict(raw_config)

    def load_from_dict(self, raw_config: dict) -> List[ModelConfig]:
        return [
            ModelConfig(**item)
            for item in raw_config.get("models", [])
        ]