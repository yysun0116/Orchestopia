import re
from pydantic import BaseModel
from typing import Dict, List, Tuple
from collections import defaultdict, deque

from orchestopia.registry import ResourceRegistry
from orchestopia.output_format.factory import FormatFactory
from orchestopia.output_format.config import FormatConfig

class FormatLoader(BaseModel):
    registry: ResourceRegistry
    factory: FormatFactory

    model_config = {
        "arbitrary_types_allowed": True
    }

    def load(self, config: FormatConfig) -> None:
        if config.display_name in self.registry.formats.snapshot():
            print(f"Output format `{config.display_name}` is already in the registry, skip loading...")
            pass
        else:
            format_basemodel = self.factory.create(config, self.registry)
            self.registry.formats.register(config.display_name, format_basemodel)
            print(f"Output format `{config.display_name}` is registered successfully!")

    def load_all(self, configs: list[FormatConfig]) -> None:
        config_map, in_degree, adj = self._check_item_dependency(configs)
        sorted_formats = self._topology_sorting(config_map, in_degree, adj)
        for format_name in sorted_formats:
            self.load(config_map[format_name])
    
    def _check_item_dependency(
            self, configs: list[FormatConfig]
        ) -> Tuple[Dict[str, FormatConfig], Dict[str, int], Dict[str, List[str]]]:
        # The config map
        config_map = {config.display_name: config for config in configs}
        # The format depends on how many other format there are
        in_degree = {config.display_name: 0 for config in configs}
        # The adjacency dict, indicate which format depend on the specific format
        adj = defaultdict(list)

        pattern = r"@format:(\w+)"
        for config in configs:
            deps = []
            for field_name in config.fields.keys():
                deps.extend(re.findall(pattern, config.fields[field_name].type))
            
            for dep in deps:
                if dep in config_map: # check if the format is in the config list
                    adj[dep].append(config.display_name)
                    in_degree[config.display_name] += 1
                else:
                    raise ValueError(f"The format `{config.display_name}` depends on a non-existent format `{dep}`. Please check for a typo or a missing format.")
        
        return config_map, in_degree, adj
    
    def _topology_sorting(self, config_map: Dict[str, FormatConfig], in_degree: Dict[str, int], adj: Dict[str, List[str]]):
        queue = deque(sorted(
            [n for n in in_degree if in_degree[n] == 0]
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
        
        if len(sorted_items) < len(config_map):
            raise ValueError("Circular dependency detected! Please check the format configuration files.")

        return sorted_items
