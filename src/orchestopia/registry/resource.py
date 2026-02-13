import re
from typing import List
from pydantic import BaseModel
from pydantic_ai.models.openai import Model
from pydantic_ai import Tool, Agent

from orchestopia.utils import resolve_basemodel_type, get_namespace_and_key
from orchestopia.registry.base import BaseRegistry

FormatRegistry = BaseRegistry[type[BaseModel]]
ModelRegistry = BaseRegistry[type[Model]]
ToolRegistry = BaseRegistry[type[List[Tool]]]
AgentRegistry = BaseRegistry[type[Agent]]


class ResourceRegistry:
    formats = FormatRegistry()
    models = ModelRegistry()
    tools = ToolRegistry()
    agents = AgentRegistry()

    def snapshot(self):
        return {
            "formats": self.formats.snapshot(),
            "models": self.models.snapshot(),
            "tools": self.tools.snapshot(),
            "agents": self.agents.snapshot(),
        }
    
    def resolve_reference(self, raw_reference: str):
        if not isinstance(raw_reference, str):
            return raw_reference  # 如果本來就不是字串，直接回傳

        if raw_reference.startswith("@"): # 從已註冊的instance中取出, e.g., @mcp_tool:rewriter
            return self.get_instance_with_namespace(raw_reference)
        elif "@" in raw_reference:  # complex type with namespace, e.g., Union[@format:CostumType, str]
            return self._resolve_complex_type_with_namespace(raw_reference)
        else:
            try:
                return resolve_basemodel_type(raw_reference, self.formats.snapshot()) # Other types
            except ValueError:
                return raw_reference  # normal string
    
    def get_instance_with_namespace(self, key_with_namespace: str) -> type:
        namespace, key = get_namespace_and_key(key_with_namespace)
        if namespace == "model":
            return self.models.get(key)
        elif namespace == "format":
            return self.formats.get(key)
        elif namespace == "mcp_tool":
            return self.tools.get(key)
        elif namespace == "agent":
            return self.agents.get(key)
        else:
            raise ValueError(f"Unknown namespace: {namespace}")

    def _resolve_complex_type_with_namespace(self, key_with_namespace: str) -> type:
        pattern = r"@(\w+):(\w+)"
        #matches = re.findall(pattern, key_with_namespace)
        def replace_namespace(match):
            namespace, key = match.groups()
            return key
        resolved_key = re.sub(pattern, replace_namespace, key_with_namespace)
        return resolve_basemodel_type(resolved_key, self.formats.snapshot())
