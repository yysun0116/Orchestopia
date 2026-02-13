from pydantic import BaseModel

from orchestopia.registry import ResourceRegistry
from orchestopia.mcp_tool.factory import MCPToolFactory
from orchestopia.mcp_tool.config import MCPToolConfig

class MCPToolLoader(BaseModel):
    registry: ResourceRegistry
    factory: MCPToolFactory

    model_config = {
        "arbitrary_types_allowed": True
    }

    async def load(self, config: MCPToolConfig) -> None:
        if config.name in self.registry.tools.snapshot():
            print(f"MCP server `{config.name}` is already in the registry, skip loading...")
            pass
        else:
            tools = await self.factory.create(config, mode = "session_based")
            if tools:
                self.registry.tools.register(config.name, tools)
                print(f"MCP server `{config.name}` is registered successfully!")
            else:
                print(f"Failed to register MCP server `{config.name}`")

    async def load_all(self, configs: list[MCPToolConfig]) -> None:
        for config in configs:
            if config.enable == True:
                await self.load(config)
