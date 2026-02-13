from pydantic import BaseModel
from pydantic_ai.models.openai import (
    OpenAIModel,
    OpenAIResponsesModel,
    Model,
    OpenAIResponsesModelSettings,
)
from pydantic_ai.settings import ModelSettings

from orchestopia.model.config import ModelConfig


class ModelFactory(BaseModel):
    def create(
            self, config: ModelConfig,
        ) -> type[Model]:
        # for chat completions api
        if config.type == "completions":
            model_settings = ModelSettings(
                **config.settings,
            )
            return OpenAIModel(
                model_name=config.model_name,
                provider=config.provider,
                settings=model_settings,
            )
        # for responses api
        elif config.type == "responses":
            model_settings = OpenAIResponsesModelSettings(
                **config.settings,
            )
            return OpenAIResponsesModel(
                model_name=config.model_name,
                provider=config.provider,
                settings=model_settings,
            )
        else:
            raise ValueError(
                f"Unknown model type: {config.type} for model {config.display_name}"
            )
    
