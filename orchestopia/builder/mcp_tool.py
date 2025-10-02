from typing import Dict, Any
from pydantic_ai.mcp import (
    MCPServerSSE,
    MCPServerStdio,
    MCPServerStreamableHTTP,
    MCPServer,
)


def build_mcp_tools(mcp_tool_config: Dict[str, Any]) -> Dict[str, type[MCPServer]]:
    mcp_tools: dict[str, type[MCPServer]] = {}
    for args in mcp_tool_config["mcp_tools"]:
        tool_name = args.pop("name", None)
        if not tool_name:
            raise ValueError(
                "`name` of the tool must be specified in the configuration..."
            )

        tool_type = args.pop("type", None)
        if not tool_type:
            raise ValueError(
                f"Tool {tool_name} must specify a `type` in the configuration..."
            )

        if tool_type == "stdio":
            reserved_keys = {"command", "args", "timeout", "env"}
            extra_args = {k: v for k, v in args.items() if k not in reserved_keys}
            mcp_tools[tool_name] = MCPServerStdio(
                command=args.get("command", ""),
                args=args.get("args", "").split(" "),
                timeout=args.get("timeout", 5),
                env=args.get("env", {}),
                **extra_args,
            )
        elif tool_type == "sse":
            if not args.get("url", None):
                raise ValueError(f"`url` should be provided in {tool_type} mcp tool...")
            reserved_keys = {"url", "timeout"}
            extra_args = {k: v for k, v in args.items() if k not in reserved_keys}
            mcp_tools[tool_name] = MCPServerSSE(
                url=args.get("url", ""),
                timeout=args.get("timeout", 5),
                **extra_args,
            )
        elif tool_type == "streamable-http":
            if not args.get("url", None):
                raise ValueError(f"`url` should be provided in {tool_type} mcp tool...")
            reserved_keys = {"url", "timeout"}
            extra_args = {k: v for k, v in args.items() if k not in reserved_keys}
            mcp_tools[tool_name] = MCPServerStreamableHTTP(
                url=args.get("url"),
                timeout=args.get("timeout", 5),
                **extra_args,
            )
        else:
            raise ValueError(f"Unknown MCP tool type: {tool_type} for tool {tool_name}")
    return mcp_tools
