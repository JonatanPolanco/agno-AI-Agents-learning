from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools
from agno.team import Team

web_agent = Agent(
    name="Web Agent",
    role="Search the web for information",
    model=Gemini(id="gemini-2.0-flash", vertexai=True, project_id="start-up-ocai", location="us-central1"),
    tools=[DuckDuckGoTools()],
    instructions="Always include sources",
    show_tool_calls=True,
    markdown=True,
)

finance_agent = Agent(
    name="Finance Agent",
    role="Get financial data",
    model=Gemini(id="gemini-2.0-flash", vertexai=True, project_id="start-up-ocai", location="us-central1"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True)],
    instructions="Use tables to display data",
    show_tool_calls=True,
    markdown=True,
)

agent_team = Team(
    mode="coordinate",
    members=[web_agent, finance_agent],
    model=Gemini(id="gemini-2.0-flash", vertexai=True, project_id="start-up-ocai", location="us-central1"),
    success_criteria="A comprehensive financial news report with clear sections and data-driven insights.",
    instructions=["Always include sources", "Use tables to display data"],
    show_tool_calls=True,
    markdown=True,
)

agent_team.print_response("What's the market outlook and financial performance of AI semiconductor companies?", stream=True)