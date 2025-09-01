import os
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.yfinance import YFinanceTools
from agno.tools.reasoning import ReasoningTools

BASEDIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASEDIR, '.env'))

agent = Agent(
    model=Gemini(
        id=os.environ.get('DEFAULT_MODEL'),
        vertexai=os.environ.get('GOOGLE_GENAI_USE_VERTEXAI'),
        project_id=os.environ.get('GOOGLE_CLOUD_PROJECT_ID'),
        location=os.environ.get('GOOGLE_CLOUD_LOCATION'),
    ),
    instructions=[
        "Use tables to display data.",
        "Include sources for all your answers.",
        "Only include the report in your response, do not include any other text.",
    ],
    tools=[
        ReasoningTools(add_instructions=True),
        YFinanceTools(
            stock_price=True,
            analyst_recommendations=True,
            company_info=True,
            company_news=True,
        )        
    ],
)
agent.print_response(
    "Write a report on AAPL?", 
    stream=True,
    show_full_reasoning=True,
    stream_intermediate_steps=True
)
