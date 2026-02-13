from typing import Union, List
from pydantic import BaseModel
from pydantic_ai.mcp import (
    MCPServerSSE,
    MCPServerStdio,
    MCPServerStreamableHTTP,
    MCPServer,
)
from pydantic_ai.tools import ToolFuncContext
from pydantic_ai import Tool

from orchestopia.mcp_tool.session_manager import MCPClient, MCPSessionManager
from orchestopia.mcp_tool.config import MCPToolConfig

class MCPToolFactory(BaseModel):
    mcp_session_manager: MCPSessionManager

    model_config = {
        "arbitrary_types_allowed": True
    }

    async def create(
        self, config: MCPToolConfig, mode: str = "session_based"
    ) -> Union[List[MCPServer], List[Tool]]:
        if mode == "agent_based":
            # connet to server
            return [self._agent_based_connect_to_server(config)]
        elif mode == "session_based":
            # connet to server
            mcp_client = await self.mcp_session_manager.connect_to_server(config)
            if mcp_client:
                # convert mcp server tools to pydanticAI tools
                pydanticai_tools = await self._mcp_to_pydanticai_tool(mcp_client)
                return pydanticai_tools
            else:
                return None
    
    def _agent_based_connect_to_server(self, config: MCPToolConfig):
        if config.type == "stdio":
            tool = MCPServerStdio(
                command=config.command,
                args=config.args,
                timeout=config.timeout,
                env=config.env,
            )
        elif config.type == "sse":
            tool = MCPServerSSE(
                url=config.url,
                timeout=config.timeout,
            )
        elif config.type == "streamable-http":
            tool = MCPServerStreamableHTTP(
                url=config.url,
                timeout=config.timeout,
            )
        else:
            raise ValueError(f"Unknown MCP tool type: {config.type} for tool {config.name}")
        return tool
    
    def _make_tool_handler(self, client: MCPClient, mcp_tool):
        async def handler(ctx: ToolFuncContext, **kwargs):
            raw_response = await client.session.call_tool(mcp_tool.name, kwargs)
            result = self._extract_tool_result(raw_response)
            return result
        return handler
    
    def _extract_tool_result(self, raw_response):
        if raw_response is None:
            raise ValueError("Tool returned empty result...")
        elif isinstance(raw_response, dict):
            return raw_response
        elif isinstance(raw_response, BaseModel):
            try:
                raw_response.model_dump(mode = "json")
            except:
                raise ValueError(f"Tool's response can't be parsed, raw response: {raw_response}")
        else:
            raise ValueError(f"Tool's response can't be parsed, raw response: {raw_response}")
    
    async def _mcp_to_pydanticai_tool(self, mcp_client: MCPClient) -> List[Tool]:
        pydanticai_tools: List[Tool] = []
        mcp_tools = await mcp_client.get_tools()
        for mcp_tool in mcp_tools:
            tool_name = f"{mcp_client.name}__{mcp_tool.name}"
            tool_handler = self._make_tool_handler(mcp_client, mcp_tool)
            pydanticai_tools.append(
                Tool.from_schema(
                    function=tool_handler,
                    name=tool_name,
                    description=mcp_tool.description or "",
                    json_schema=mcp_tool.outputSchema,
                )
            )
        return pydanticai_tools
    

    