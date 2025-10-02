from typing import Dict
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import Model
from pydantic_ai.mcp import MCPServer
import toml
from pathlib import Path

from format import build_formats
from agent import build_agents
from mcp_tool import build_mcp_tools
from model import build_models


class Registry(BaseModel):
    models: Dict[str, type[Model]] = Field(default={})
    formats: Dict[str, type[BaseModel]] = Field(default={})
    mcp_tools: Dict[str, type[MCPServer]] = Field(default={})
    agents: Dict[str, type[Agent]] = Field(default={})


    def build(self) -> None:
        model_config = toml.load(f"{Path(__file__).resolve().parent.parent}/config/model.toml")
        structured_output_config = toml.load(f"{Path(__file__).resolve().parent.parent}/config/format.toml")
        mcp_tool_config = toml.load(f"{Path(__file__).resolve().parent.parent}/config/mcp_tool.toml")
        agent_config = toml.load(f"{Path(__file__).resolve().parent.parent}/config/agent.toml")
        
        self.models = build_models(model_config)
        self.formats = build_formats(structured_output_config)
        self.mcp_tools = build_mcp_tools(mcp_tool_config)
        self.agents = build_agents(agent_config, )