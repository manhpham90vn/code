"""Base class cho tools."""


class Tool:
    name: str
    description: str
    input_schema: dict

    @classmethod
    def get_tool_definition(cls) -> dict:
        return {
            "name": cls.name,
            "description": cls.description,
            "input_schema": cls.input_schema,
        }

    @classmethod
    def execute(cls, input_data: dict) -> str:
        raise NotImplementedError
