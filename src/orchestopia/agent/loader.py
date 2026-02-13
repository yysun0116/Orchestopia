from pydantic import BaseModel
from typing import Tuple, Dict, List
from collections import defaultdict, deque

from orchestopia.registry import ResourceRegistry
from orchestopia.agent.factory import AgentFactory
from orchestopia.agent.config import AgentConfig

class AgentLoader(BaseModel):
    registry: ResourceRegistry
    factory: AgentFactory

    model_config = {
        "arbitrary_types_allowed": True
    }

    async def load(self, config: AgentConfig) -> None:
        if config.name in self.registry.agents.snapshot():
            print(f"Agent `{config.name}` is already in the registry, skip loading...")
            pass
        else:
            agent, agent_tool = await self.factory.create(config, self.registry)
            self.registry.agents.register(config.name, agent)
            if agent_tool:
                self.registry.tools.register(f"agent__{config.name}", [agent_tool])
            print(f"Agent `{config.name}` is registered successfully!")

    async def load_all(self, configs: list[AgentConfig]) -> None:
        config_map, in_degree, adj = self._check_item_dependency(configs)
        sorted_agents = self._topology_sorting(config_map, in_degree, adj)
        for agent_name in sorted_agents:
            config = config_map[agent_name]
            await self.load(config)
    
    def _check_item_dependency(
            self, configs: list[AgentConfig]
        ) -> Tuple[Dict[str, AgentConfig], Dict[str, int], Dict[str, List[str]]]:
        # The config map
        config_map = {config.name: config for config in configs}
        # The agent depends on how many other agents there are
        in_degree = {config.name: 0 for config in configs}
        # The adjacency dict, indicate which agent depend on the specific agent
        adj = defaultdict(list)

        for config in configs:
            if config.type == "a2a_subagent":
                deps = []
            else:
                deps = [tool.split(":")[1].strip() for tool in config.toolsets if tool.startswith("@agent:")]
            for dep in deps:
                if dep in config_map: # check if the agent is in the config list
                    adj[dep].append(config.name)
                    in_degree[config.name] += 1
                else:
                    raise ValueError(f"The agent `{config.name}` depends on a non-existent agent `{dep}`. Please check for a typo or a missing agent.")
        
        return config_map, in_degree, adj
    
    def _topology_sorting(self, config_map: Dict[str, AgentConfig], in_degree: Dict[str, int], adj: Dict[str, List[str]]):
        queue = deque(sorted(
            [n for n in in_degree if in_degree[n] == 0],
            key=lambda x: 1 if config_map[x].type == "orchestrator" else 0 # Put the orchestrator at the end of the queue
        ))

        sorted_items = []
        while queue:
            u_name = queue.popleft()
            sorted_items.append(u_name)
            for v_name in adj[u_name]:
                # The item (u_name) that v_name depends on is added to the list, and the degree of v_name is decremented by 1
                in_degree[v_name] -= 1
                # If all the items that v_name depends on have been added to the list, v_name can be put into the queue.
                if in_degree[v_name] == 0:
                    queue.append(v_name)
                    if len(queue) > 1:
                        new_q = sorted(list(queue), key=lambda x: 1 if config_map[x].type == "orchestrator" else 0)
                        queue = deque(new_q)
        
        if len(sorted_items) < len(config_map):
            raise ValueError("Circular dependency detected! Please check the agent configuration files.")

        return sorted_items
            
