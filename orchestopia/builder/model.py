from typing import Dict, Any
from pydantic_ai.models.openai import (
    OpenAIModel,
    OpenAIResponsesModel,
    Model,
    OpenAIResponsesModelSettings,
)
from pydantic_ai.settings import ModelSettings
from pydantic_ai.providers.openai import OpenAIProvider


def build_models(model_config: Dict[str, Any]) -> Dict[str, type[Model]]:
    models: dict[str, type[Model]] = {}

    for args in model_config["models"]:
        display_name = args.pop("display_name", args.get("model_name"))
        provider_config = args.get("provider", {})
        provider = OpenAIProvider(
            base_url=provider_config.get("base_url", ""),
            api_key=provider_config.get("api_key", ""),
        )
        model_settings_config = args.get("settings", {})

        if args.get("type") == "completions":
            model_settings = ModelSettings(
                **model_settings_config,
            )
            models[display_name] = OpenAIModel(
                model_name=args["model_name"],
                provider=provider,
                settings=model_settings,
            )
        elif args.get("type") == "responses":
            model_settings = OpenAIResponsesModelSettings(
                **model_settings_config,
            )
            models[display_name] = OpenAIResponsesModel(
                model_name=args["model_name"],
                provider=provider,
                settings=model_settings,
            )
        else:
            raise ValueError(
                f"Unknown model type: {args.get('type')} for model {display_name}"
            )
    return models
