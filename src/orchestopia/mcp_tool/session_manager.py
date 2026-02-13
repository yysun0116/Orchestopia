from contextlib import AsyncExitStack
from typing import Dict, Optional, List
from datetime import timedelta
from dataclasses import dataclass

from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client
from mcp import ClientSession, StdioServerParameters, Tool
from tenacity import retry, stop_after_attempt, wait_exponential
import asyncio

from orchestopia.mcp_tool.config import MCPToolConfig

@dataclass
class MCPClient:
    name: str
    session: ClientSession
    exit_stack: AsyncExitStack
    server_params: dict
    
    async def get_tools(self) -> List[Tool]:
        mcp_tools = await self.session.list_tools()
        return mcp_tools.tools

class MCPSessionManager:
    def __init__(self):
        self.clients: Dict[str, MCPClient] = {}
        self._tool_configs: Dict[str, MCPToolConfig] = {}
        self._lock = asyncio.Lock()
    
    async def connect_to_server(self, config: MCPToolConfig) -> MCPClient:
        self._tool_configs[config.name] = config
        if config.type == "stdio":
            mcp_client = await self.safe_connect(
                config.name,
                self._connect_stdio(
                    name=config.name,
                    command=config.command,
                    args=config.args,
                    timeout=config.timeout
                )
            )
        elif config.type == "sse":
            mcp_client = await self.safe_connect(
                config.name, 
                self._connect_sse(
                    name=config.name,
                    url=config.url,
                    timeout=config.timeout
                )
            )
        elif config.type == "streamable-http":
            mcp_client = await self.safe_connect(
                config.name, 
                self._connect_streamable_http(
                    name=config.name,
                    url=config.url,
                    timeout=config.timeout
                )
            )
        else:
            raise ValueError(f"Unknown MCP tool type: {config.type} for tool {config.name}")
        return mcp_client

    async def safe_connect(self, name: str, connect_coroutine, timeout=60):
        try:
            return await asyncio.wait_for(connect_coroutine, timeout)
        except asyncio.CancelledError:
            print(
                f"Connection to MCP server '{name}' was cancelled. (Server may be unreachable or shutdown in progress)."
            )
            raise

        except asyncio.TimeoutError as e:
            raise RuntimeError(f"Timeout connecting to `{name}` server") from e

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def _connect_stdio(
        self, name: str, command: str, args: list[str], timeout: int = 60
    ) -> MCPClient:
        async with self._lock:
            if name in self.clients:
                return self.clients[name]
            
            exit_stack = AsyncExitStack()
            try:
                server_params = StdioServerParameters(command=command, args=args)
                stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
                # establish communication channel
                read, write = stdio_transport
                session = await exit_stack.enter_async_context(
                    ClientSession(
                        read, 
                        write, 
                        read_timeout_seconds=timedelta(seconds=timeout)
                    )
                )
                # initialize MCP session
                await session.initialize()
                
                self.clients[name] = MCPClient(
                    name = name,
                    session = session,
                    exit_stack = exit_stack,
                    server_params = {
                        "command": command,
                        "args": args
                    }
                )
                print(f"MCP session '{name}' (stdio) connected.") # TODO:改成logger
                return self.clients[name]
            except Exception as e:
                await exit_stack.aclose()
                print(f"Failed to connect MCP session '{name}' (stdio): {e}")
                raise
    
    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def _connect_sse(
        self, name: str, url: str, timeout: int = 60
    ) -> MCPClient:
        async with self._lock:
            if name in self.clients:
                return self.clients[name]
            
            exit_stack = AsyncExitStack()
            try:
                read, write = await exit_stack.enter_async_context(sse_client(url))
                session = await exit_stack.enter_async_context(
                    ClientSession(
                        read, 
                        write, 
                        read_timeout_seconds=timedelta(seconds=timeout)
                    )
                )
                # initialize MCP session
                await session.initialize()

                self.clients[name] = MCPClient(
                    name = name,
                    session = session,
                    exit_stack = exit_stack,
                    server_params = {
                        "url": url
                    }
                )
                print(f"MCP session '{name}' (sse) connected.") # TODO:改成logger
                return self.clients[name]
            except Exception as e:
                await exit_stack.aclose()
                print(f"Failed to connect MCP session '{name}' (sse): {e}")
                raise
    
    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def _connect_streamable_http(
        self, name: str, url: str, timeout: int = 60
    ) -> MCPClient:
        if name in self.clients:
            return self.clients[name]
        
        exit_stack = AsyncExitStack()
        async with self._lock:
            try:
                read, write, get_session_id = await exit_stack.enter_async_context(streamable_http_client(url))
                session = await exit_stack.enter_async_context(
                    ClientSession(
                        read, 
                        write, 
                        read_timeout_seconds=timedelta(seconds=timeout)
                    )
                )
                # initialize MCP session
                await session.initialize()

                self.clients[name] = MCPClient(
                    name = name,
                    session = session,
                    exit_stack = exit_stack,
                    server_params = {
                        "url": url
                    }
                )
                print(f"MCP session '{name}' (streamableHTTP) connected.") # TODO:改成logger
                return self.clients[name]
            except Exception as e:
                await exit_stack.aclose()
                print(f"Failed to connect MCP session '{name}' (streamableHTTP): {e}")
                raise
    
    def get_session(self, name: str) -> Optional[ClientSession]:
        client = self.get_client(name)
        return client.session if client else None
    
    def get_client(self, name: str) -> Optional[MCPClient]:
        return self.clients.get(name)
    
    async def get_tools(self, name: str) -> List[Tool]:
        client = self.clients.get(name)
        if not client:
            raise KeyError(f"MCP client '{name}' not found")
        return await client.get_tools()
    
    async def disconnect(self, name: str):
        """disconnect specific mcp sever"""
        async with self._lock:
            if name in self.clients:
                await self.clients[name].exit_stack.aclose()
                del self.clients[name]
                print(f"MCP session '{name}' disconnected.") # TODO:改成logger

    async def disconnect_all(self):
        """disconnect all connection"""
        if not self.clients:
            return
        names = list(self.clients.keys())
        await asyncio.gather(*(self.disconnect(name) for name in names), return_exceptions=True)
    


    