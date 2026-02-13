from pydantic import BaseModel, Field, TypeAdapter, field_validator
from typing import Literal, Dict, Optional, Union, Annotated, List
from pathlib import Path
import yaml

class MCPToolConfigBase(BaseModel):
    name: str 
    type: Literal["stdio", "sse", "streamable-http"]
    enable: bool = True
    timeout: int = Field(default=60)

class MCPToolConfigStdio(MCPToolConfigBase):
    type: Literal["stdio"]
    command: str
    args: str
    env: Optional[Dict[str, str]] = None

    @field_validator("args", mode="after")
    def spilt_args(cls, args_string):
        return args_string.split(" ")

class MCPToolConfigSse(MCPToolConfigBase):
    type: Literal["sse"]
    url: str

class MCPToolConfigStreamableHTTP(MCPToolConfigBase):
    type: Literal["streamable-http"]
    url: str



MCPToolConfig = Annotated[
    Union[MCPToolConfigStdio, MCPToolConfigSse, MCPToolConfigStreamableHTTP],
    Field(discriminator="type"),
]

class MCPToolConfigLoader(BaseModel):
    _adapter = TypeAdapter(MCPToolConfig)
    
    @classmethod
    def load_from_yaml(
        cls, config_path: str = f"{Path(__file__).resolve().parent.parent.parent}/config"
    ) -> List[MCPToolConfig]:
        instance = cls()
        # read yaml
        with open(f"{config_path}/mcp_tool.yaml") as f:
            raw_config = yaml.safe_load(f)
        # convert into MCPToolConfig
        return instance.load_from_dict(raw_config)

    def load_from_dict(self, raw_config: dict) -> List[MCPToolConfig]:
        return [
            self._adapter.validate_python(tool_info)
            for tool_info in raw_config.get("mcp_tools", [])
        ]