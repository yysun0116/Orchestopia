from pydantic import BaseModel, create_model

from orchestopia.output_format.config import FormatConfig
from orchestopia.registry import ResourceRegistry


class FormatFactory(BaseModel):

    def create(self, config: FormatConfig, registry: ResourceRegistry) -> None:
        # get format display name
        format_name = config.display_name

        # get name and type of fields
        model_fields = {}
        for field_name, field_value in config.fields.items():
            field_type_str = field_value.type
            default = field_value.default
            
            # resolve field type string
            resolved_type = registry.resolve_reference(field_type_str)
            model_fields[field_name] = (resolved_type, default)
        
        # Create and save the BaseModel
        return create_model(format_name, **model_fields)
