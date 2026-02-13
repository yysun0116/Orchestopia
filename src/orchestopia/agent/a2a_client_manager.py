from uuid import uuid4
from contextlib import AsyncExitStack
from typing import Dict, Optional, Union
from dataclasses import dataclass
#from fasta2a.client import A2AClient
from a2a.client import BaseClient, ClientConfig, ClientFactory, A2ACardResolver
from a2a.types import (
    TransportProtocol, 
    TaskQueryParams, 
    Message, 
    Task
)
from tenacity import retry, stop_after_attempt, wait_exponential
import asyncio
import httpx

@dataclass
class A2AAgent:
    name: str
    client: BaseClient
    exit_stack: AsyncExitStack
    server_params: dict
    
    async def run(self, query: str, context_id: str = None) -> Union[str, Message, Task]:
        message = Message(
            role="user",
            # TODO: add multimodal parts
            parts=[{"kind": "text", "text": query}],
            context_id=context_id,
            message_id = str(uuid4())
        )
        # send message to client
        async for result in self.client.send_message(message):
            task_response = result
            break

        # resolve task
        task, _ = task_response if isinstance(task_response, tuple) else (task_response, None)
        #if not isinstance(task, Task):
        if isinstance(task, Message):
            # Agent return Message instead of Task
            #print(f"Agent 直接回覆: {task.parts}")
            return task
        elif isinstance(task, Task):
            # Agent return Task -> polling until it complete
            final_task = await self._polling_task_status(task_id=task.id)
            return final_task
        else:
            raise Exception(f"The type of the response from a2a agent `{self.name}`is not Message of Task. raw response: {task}")
    
    async def _polling_task_status(
            self, task_id: str, history_length: int = 10
        ) -> Union[str, Task]:
        """
        Poll the task status until it complete and retrieve the message
        """
        print(f"Task created，ID: {task_id}，Start polling...")
        while True:
            # get the status of the task
            current_task = await self.client.get_task(
                TaskQueryParams(
                    history_length = history_length,
                    id = task_id
                )
            )
            status = current_task.status
            
            if status.state == "completed":
                return current_task
            
            elif status.state in ["failed", "canceled", "rejected"]:
                return f"The task (id: {task_id}) is {status.state}, Error message: {status.message}"
                #raise Exception(f"The task (id: {task_id}) is {status.state}, Error message: {status.message}")
            
            await asyncio.sleep(2)

    # def _extract_response_from_task(self, task: Task):
    #     for artifact in Task.artifacts:
    #         pydanticai_parts = 
    #         for part in artifact.parts:
    #             if isinstance(part, TextPart):
    #                 pydanticai_TextPart

class A2AClientManager:
    def __init__(self):
        self.agents: Dict[str, A2AAgent]
        # self.clients: Dict[str, BaseClient] = {}
        # self.exit_stacks: Dict[str, AsyncExitStack] = {}
        self._lock = asyncio.Lock()

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def connect_a2a(
        self,
        name: str,
        base_url: str,
        httpx_client: httpx.AsyncClient | None = None,
        timeout: int = 60
    ) -> A2AAgent:
        async with self._lock:
            if name in self.agents:
                return self.agents[name]

            exit_stack = AsyncExitStack()
            try:
                if httpx_client is None: # 為了統一管理，自行建立httpx_client
                    httpx_client = await exit_stack.enter_async_context(
                        httpx.AsyncClient(timeout=timeout)
                    )
                resolver = A2ACardResolver(
                    httpx_client = httpx_client,
                    base_url=base_url
                )
                # Create A2A client with the agent card
                config = ClientConfig(
                    httpx_client=httpx_client,
                    supported_transports=[
                        TransportProtocol.jsonrpc,
                        TransportProtocol.http_json,
                    ],
                    use_client_preference=True,
                )
                agent_card = await resolver.get_agent_card()
                factory = ClientFactory(config)
                a2a_client = factory.create(agent_card)

                # self.exit_stacks[name] = exit_stack
                # self.clients[name] = a2a_client
                a2a_agent = A2AAgent(
                    name = name,
                    client = a2a_client,
                    exit_stack = exit_stack,
                    server_params = {
                        "base_url": base_url
                    }
                )
                print(f"A2A agent '{name}' connected.")
                return a2a_agent

            except Exception as e:
                await exit_stack.aclose()
                print(f"Failed to connect A2A agent '{name}': {e}")
                raise
    
    def get_client(self, name: str) -> Optional[BaseClient]:
        if self.agents.get(name):
            return (self.agents.get(name)).client
    
    def get_agent(self, name: str) -> Optional[A2AAgent]:
        return self.agents.get(name)
    
    async def disconnect(self, name: str):
        """disconnect specific mcp sever"""
        async with self._lock:
            if name in self.agents:
                await self.agents[name].exit_stack.aclose()
                del self.agents[name]
                print(f"A2A client '{name}' disconnected.") # TODO:改成logger

    async def disconnect_all(self):
        """disconnect all connection"""
        if not self.agents:
            return
        names = list(self.agents.keys())
        await asyncio.gather(*(self.disconnect(name) for name in names), return_exceptions=True)
