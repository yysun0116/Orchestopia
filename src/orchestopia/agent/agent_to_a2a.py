import uvicorn
from fasta2a.schema import Skill
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.settings import ModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

provider = OpenAIProvider(
    base_url = "https://ml.gss.com.tw/gemma3",
    api_key = "sk-proxy-test",
)
setting = ModelSettings(
    max_tokens = 131072,
    temperature = 0.0,
    top_p = 1.0,
)
model = OpenAIModel(
        model_name="gemma3:27b-it-qat",
        provider=provider,
        settings = setting,
    )
agent = Agent(model, instructions='Be fun!')
app = agent.to_a2a(
    name = "orchestrator_agent",
    description = "An Agent to help user with their problem",
    skills = [
        Skill(
            id = "general_qa",
            name = "general question answering",
            description = "Answer general user questions in natural language without using external tools",
            tags = ['qa', 'no_tools'],
            input_modes=["text/plain", "application/json"],
            output_modes=["text/plain", "application/json", "text/markdown"]
        )
    ]
)
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port = 8000)