import json
from typing import Union, Tuple, List, get_args
from pydantic import BaseModel, Field
from pydantic_ai import Agent, Tool
from pydantic_ai.toolsets.function import FunctionToolset
from pydantic_ai.tools import ToolFuncContext
from pydantic_ai.messages import (
    TextPart, 
    ImageUrl, 
    DocumentUrl, 
    AudioUrl, 
    BinaryContent,
    UserContent,
    AudioMediaType,
    ImageMediaType,
    DocumentMediaType
)
from a2a.types import Message, Task, Part, FileWithBytes, FileWithUri

from orchestopia.utils import get_namespace_and_key
from orchestopia.registry.resource import ResourceRegistry
from orchestopia.agent.config import AgentConfig
from orchestopia.agent.a2a_client_manager import A2AClientManager, A2AAgent

VALID_AUDIO_TYPES = get_args(AudioMediaType)
VALID_IMAGE_TYPES = get_args(ImageMediaType)
VALID_DOC_TYPES = get_args(DocumentMediaType)


class AgentFactory(BaseModel):
    a2a_client_manager: A2AClientManager

    model_config = {
        "arbitrary_types_allowed": True
    }

    async def create(
        self, config: AgentConfig, registry: ResourceRegistry
    ) -> Agent:
        if config.type == "a2a_subagent":
            agent = await self.a2a_client_manager.connect_a2a(
                name = config.name,
                base_url = config.base_url,
            )
            agent_tool = self.convert_a2a_agent_into_tool(config, agent)
        else:
            # get extra toolset
            extra_toolset = self._get_tools_for_agent(config, registry)

            # get output_type
            output_type = self._get_output_type(config, registry)

            # create agent
            if config.type == "orchestrator":
                ## TODO: add default tools
                #default_toolset = FunctionToolset()
                ## TODO: Agent deps
                agent = Agent(
                    name=config.name,
                    model=registry.get_instance_with_namespace(config.model),
                    system_prompt=config.system_prompt,
                    instructions=config.instructions,
                    output_type=output_type,
                    toolsets= [extra_toolset] if extra_toolset else None #[default_toolset, extra_toolset]
                    # deps_type = 
                )
                agent_tool = None

            elif config.type == "local_subagent":
                agent = Agent(
                    name=config.name,
                    model=registry.get_instance_with_namespace(config.model),
                    system_prompt=config.system_prompt,
                    instructions=config.instructions,
                    output_type=output_type,
                    toolsets= [extra_toolset] if extra_toolset else None
                )
                agent_tool = self.convert_local_agent_into_tool(config, agent)
                
        return agent, agent_tool
    
    def _get_tools_for_agent(self, config: AgentConfig, registry: ResourceRegistry) -> FunctionToolset:
        extra_tools = []
        for tool_name in config.toolsets:
            namespapce, tool_name = get_namespace_and_key(tool_name)
            if namespapce == "mcp_tool": # @mcp_tool:
                mcp_tools = registry.tools.get(tool_name)
                if mcp_tools:
                    extra_tools += mcp_tools
            elif namespapce == "agent": # @agent:
                agent_tools = registry.tools.get(f"agent__{tool_name}")
                if agent_tools:
                    extra_tools += agent_tools
        extra_toolset = FunctionToolset(extra_tools)
        return extra_toolset
    
    def _get_output_type(self, config: AgentConfig, registry: ResourceRegistry):
        types =  tuple(registry.resolve_reference(ot) for ot in config.output_type)
        output_type = Union[types] if len(config.output_type) > 1 else types[0]
        return output_type
    
    # Agent to Tool
    ## local agent
    def convert_local_agent_into_tool(self, config: AgentConfig, agent: Agent) -> Tool:
        # Input schema
        class AgentInput(BaseModel):
            query: str = Field(description="Specific questions or instructions to be passed to the expert")

        # agent execution function
        async def agent_handler(ctx: ToolFuncContext, query: str) -> str:
            deps = ctx.deps if ctx.deps else None
            result = await agent.run(query, deps = deps)
            return result.output

        # convert into tool
        return Tool.from_schema(
            function = agent_handler,
            name = f"agent__{agent.name}",
            description = config.description,
            json_schema = AgentInput.model_json_schema()
        )
    ## a2a agent
    def convert_a2a_agent_into_tool(self, config: AgentConfig, agent: A2AAgent) -> Tool:
        # Input schema
        class AgentInput(BaseModel):
            query: str = Field(description="Specific questions or instructions to be passed to the expert")
        
        # agent execution function
        async def agent_handler(ctx: ToolFuncContext, query: str) -> List[UserContent]:
            # TODO: add history
            #history_message
            #context_id
            raw_response = await agent.run(query = query, context_id = None)
            
            if raw_response:
                if isinstance(raw_response, str):
                    return [raw_response]
                elif isinstance(raw_response, Task) or isinstance(raw_response, Message):
                    context_id, response = self._extract_response_from_task(raw_response)
                    return response
            else:
                return f"Failed to run the agent."
        
        # convert into tool
        return Tool.from_schema(
            function = agent_handler,
            name = f"agent__{agent.name}",
            description = config.description,
            json_schema = AgentInput.model_json_schema()
        )
    
    def _extract_response_from_task(self, raw_response: Union[Task, Message]) -> Tuple[str, List[UserContent]]:
        context_id = raw_response.context_id
        pydanticai_parts = []
        if isinstance(raw_response, Message):
            for part in raw_response.parts:
                pydanticai_parts.append(self._a2a_to_pydanticai_part(part))
        elif isinstance(raw_response, Task):
            for artifact in Task.artifacts:
                for part in artifact.parts:
                    pydanticai_parts.append(self._a2a_to_pydanticai_part(part))
        return context_id, pydanticai_parts
    
    def _a2a_to_pydanticai_part(self, part: Part) -> UserContent:
        if part.root.kind == "text":
            return part.root.text
        elif part.root.kind == "data":
            return json.dumps(part.root.data, ensure_ascii=True)
        elif part.root.kind == "file":
        #elif isinstance(part, a2a_FilePart):
            mime_type = part.file.mime_type
            if isinstance(part.file, FileWithBytes):
                pydanticai_part = BinaryContent(
                    data = part.file.bytes,
                    media_type = mime_type
                )
            elif isinstance(part.file, FileWithUri):
                if mime_type in VALID_IMAGE_TYPES:
                    pydanticai_part = ImageUrl(
                        url = part.file.uri,
                        media_type = mime_type
                    )
                elif mime_type in VALID_DOC_TYPES:
                    pydanticai_part = DocumentUrl(
                        url = part.file.uri,
                        media_type = mime_type
                    )
                elif mime_type in VALID_AUDIO_TYPES:
                    pydanticai_part = AudioUrl(
                        url = part.file.uri,
                        media_type = mime_type
                    )
                else:
                    raise Exception(f"Unknow mime type of the part. Mime type: {mime_type}")
            return pydanticai_part
        else:
            raise Exception(f"Cannot parse the part recieved from the A2A agent. Part: {part}")

    
    # TODO: 與memory整合
    def _compile_chat_history(self, history: list):
        return

        
