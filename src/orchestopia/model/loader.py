from pydantic import BaseModel
from orchestopia.registry import ResourceRegistry

from orchestopia.model.factory import ModelFactory
from orchestopia.model.config import ModelConfig

class ModelLoader(BaseModel):
    registry: ResourceRegistry
    factory: ModelFactory

    model_config = {
        "arbitrary_types_allowed": True
    }

    def load(self, config: ModelConfig) -> None:
        if config.display_name in self.registry.models.snapshot():
            print(f"Model `{config.display_name}` is already in the registry, skip loading...")
            pass
        else:
            model = self.factory.create(config)
            self.registry.models.register(config.display_name, model)
            print(f"Model `{config.display_name}` is registered successfully!")

    def load_all(self, configs: list[ModelConfig]) -> None:
        for config in configs:
            self.load(config)
