from pydantic import BaseModel, constr, field_validator, TypeAdapter, Field
from typing import Optional, List, Literal, Union, Annotated
from pathlib import Path
import yaml

class BaseAgentConfig(BaseModel):
    name: str
    type: Literal['orchestrator', 'local_subagent', 'a2a_subagent']
    description: str = None

class LocalAgentConfig(BaseAgentConfig):
    name: str
    type: Literal['orchestrator', 'local_subagent']
    model: str = constr(pattern=r'^@model:.*$')
    description: str = None
    system_prompt: Optional[str] = ()
    instructions: str
    output_type: List[str] = ["str"]
    toolsets: List[str] = []
    retries: int = 3

    @field_validator("output_type")
    def check_output_type(cls, output_type):
        for ot in output_type:
            if ot != "str" and not ot.startswith("@format:"):
                raise ValueError('`output_type` must be "str" or start with "@format:"')
        return output_type

    @field_validator("toolsets")
    def check_toolsets(cls, toolsets):
        for tool in toolsets:
            if not tool.startswith("@mcp_tool:") and not tool.startswith("@agent:"):
                raise ValueError('`toolsets` must start with "@mcp_tool:" or "@agent:"')
        return toolsets

class A2AAgentConfig(BaseAgentConfig):
    name: str
    type: Literal['a2a_subagent']
    base_url: str

AgentConfig = Annotated[
    Union[LocalAgentConfig, A2AAgentConfig],
    Field(discriminator="type"),
]

class AgentConfigLoader(BaseModel):
    _adapter = TypeAdapter(AgentConfig)

    @classmethod
    def load_from_yaml(
        cls, config_path: str = f"{Path(__file__).resolve().parent.parent.parent}/config"
    ) -> List[AgentConfig]:
        instance = cls()
        # read yaml
        with open(f"{config_path}/agent.yaml") as f:
            raw_config = yaml.safe_load(f)
        # convert into AgentConfig
        return instance.load_from_dict(raw_config)

    def load_from_dict(self, raw_config: dict) -> List[AgentConfig]:
        return [
            self._adapter.validate_python(agent_info)
            for agent_info in raw_config.get("agents", [])
        ]