import re
from typing import Dict, Any
from pydantic_ai import Agent

from utils import Registry
from format import resolve_basemodel_type


def get_custom_type_from_namespace(value: str, registry: Registry) -> type:
    try:
        namespace, key = value[1:].split(":", 1)
    except ValueError:
        raise ValueError(f"Invalid reference format: {value}")
    if namespace == "model":
        return registry.models[key]
    elif namespace == "format":
        return registry.formats[key]
    elif namespace == "mcp_tool":
        return registry.mcp_tools[key]
    else:
        raise ValueError(f"Unknown namespace: {namespace}")


def resolve_type_with_namespace(value: str, custom_formats: dict[str, type]) -> type:
    pattern = r"@(\w+):(\w+)"
    matches = re.findall(pattern, value)
    for namespace, key in matches:
        value = re.sub(rf"@{namespace}:{key}", key, value)
    return resolve_basemodel_type(value, custom_formats)


def resolve_reference(value: str, registry: Registry):
    if not isinstance(value, str):
        return value  # 如果本來就不是字串，直接回傳

    if value.startswith("@"):
        return get_custom_type_from_namespace(value, registry)
    elif "@" in value:  # complex type with namespace
        return resolve_type_with_namespace(value, registry.formats)
    else:
        try:
            return resolve_basemodel_type(value, registry.formats)  # Other types
        except ValueError:
            return value  # normal string


def build_agents(
    agent_config: Dict[str, Any], registry: Registry
) -> Dict[str, type[Agent]]:
    agents: dict[str, type[Agent]] = {}
    for args in agent_config["agents"]:
        agent_name = args.get("name", None)
        if not agent_name:
            raise ValueError("Each agent must have a `name`...")

        reserved_keys = {"name", "model", "instructions", "output_type", "toolsets"}
        extra_args = {k: v for k, v in args.items() if k not in reserved_keys}
        agents[agent_name] = Agent(
            name=args.get("name", None),
            model=resolve_reference(args.get("model", None), registry),
            instructions=args.get("instructions", None),
            output_type=resolve_reference(args.get("output_type", None), registry),
            toolsets=[
                resolve_reference(tool, registry) for tool in args.get("toolsets", None)
            ]  # multiple tools
            if args.get("toolsets", None)
            else None,
            **extra_args,
        )
    return agents
