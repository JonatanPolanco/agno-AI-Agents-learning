"""
🗞️ Multi-Agent Finance & News Team with Fact-Checking & Classification
-------------------------------------------------------------------
Architecture:
User Query → QueryClassifier → (FactChecker if needed) → Agents → Aggregator → Final Response

This ensures:
- False or unverifiable premises → gracefully clarified
- Pure finance queries → direct analysis
- Mixed queries → fact-check + finance analysis
"""

from typing import List, Optional, Dict
import typer
import os
from dotenv import load_dotenv

from agno.agent import Agent
from agno.models.google import Gemini
from agno.team.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools
from agno.storage.sqlite import SqliteStorage
from rich import print

load_dotenv()

# === Storage in SQLite ===
team_storage = SqliteStorage(table_name="finance_team", db_file="tmp/agents.db")

# === Agent Definitions ===
web_agent = Agent(
    name="web-agent",
    role="Search the web for information",
    model=Gemini(
        id=os.environ.get("DEFAULT_MODEL"),
        api_key=os.environ.get("GOOGLE_API_KEY"),
    ),
    tools=[DuckDuckGoTools()],
    instructions="You are a skilled web researcher specializing in market-moving news.",
    show_tool_calls=True,
    markdown=True,
)

finance_agent = Agent(
    name="finance-agent",
    role="Get financial data",
    model=Gemini(
        id=os.environ.get("DEFAULT_MODEL"),
        api_key=os.environ.get("GOOGLE_API_KEY"),
    ),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True)],
    instructions="You are a skilled financial analyst with expertise in market data.",
    show_tool_calls=True,
    markdown=True,
)

# === Fact Checking Layer ===
class FactChecker:
    """
    Validates user queries by searching for factual evidence.
    Returns standardized results: verified, false, or uncertain.
    """

    def __init__(self, web_agent: Agent):
        self.web_agent = web_agent

    def check(self, query: str) -> Dict:
        search_results = self.web_agent.run(query)
        text = str(search_results).lower()

        if not search_results or "no results" in text:
            return {"status": "false", "reason": "No evidence found in recent reports."}
        elif "uncertain" in text or "rumor" in text or "unverified" in text:
            return {"status": "uncertain", "reason": "Conflicting or insufficient evidence."}
        else:
            return {"status": "verified", "reason": "Evidence found in multiple sources."}

# === Query Classifier ===
class QueryClassifier:
    """
    Classifies queries into categories:
    - 'fact_check'   → requires validation of premise
    - 'finance_only' → direct financial analysis
    - 'mixed'        → both news & finance
    """

    def classify(self, query: str) -> str:
        q = query.lower()
        if any(keyword in q for keyword in [
            "trump", "biden", "war", "attack", "venezuela",
            "election", "sanction", "geopolitics", "conflict"
        ]):
            return "fact_check"
        elif any(ticker in q for ticker in [
            "amzn", "msft", "googl", "meta", "snap",
            "ttwo", "ea", "atvi", "nvda", "amd", "jpm", "bac"
        ]):
            return "finance_only"
        else:
            return "mixed"

# === Query Router ===
class QueryRouter:
    """
    Routes the user query depending on classification + fact-check results.
    """

    def __init__(self, agents: Dict[str, Agent], fact_checker: FactChecker, classifier: QueryClassifier, team: Team):
        self.agents = agents
        self.fact_checker = fact_checker
        self.classifier = classifier
        self.team = team

    def route(self, query: str) -> str:
        category = self.classifier.classify(query)

        if category == "finance_only":
            return self.run_agents(query)

        elif category == "fact_check":
            check_result = self.fact_checker.check(query)
            return self._handle_fact_check(query, check_result)

        else:  # mixed
            check_result = self.fact_checker.check(query)
            if check_result["status"] == "verified":
                return self.run_agents(query)
            else:
                return self._handle_fact_check(query, check_result)

    def _handle_fact_check(self, query: str, check_result: Dict) -> str:
        if check_result["status"] == "false":
            return f"⚠️ No recent reports confirm this. {check_result['reason']} Would you like me to run a hypothetical analysis instead?"
        elif check_result["status"] == "uncertain":
            return f"🤔 I couldn’t fully verify this. {check_result['reason']} Should I proceed hypothetically?"
        else:
            return self.run_agents(query)

    def run_agents(self, query: str) -> str:
        response = self.team.run(query)
        if hasattr(response, "content"):
            return response.content
        elif isinstance(response, dict) and "content" in response:
            return response["content"]
        elif isinstance(response, str):
            return response
        else:
            return str(response)

# === Finance Team Setup ===
def finance_team(user: str = "user"):
    """
    Launches the finance team CLI with classification, fact-checking, and routing.
    """
    session_id: Optional[str] = None

    new = typer.confirm("Do you want to start a new session?")
    if not new:
        existing_sessions: List[str] = team_storage.get_all_session_ids(user)
        if len(existing_sessions) > 0:
            session_id = existing_sessions[0]

    agent_team = Team(
        members=[web_agent, finance_agent],
        model=Gemini(
            id=os.environ.get("DEFAULT_MODEL"),
            api_key=os.environ.get("GOOGLE_API_KEY"),
        ),
        storage=team_storage,
        user_id=user,
        session_id=session_id,
        mode="coordinate",
        success_criteria="A comprehensive financial news report with data-driven insights.",
        instructions="You are the lead editor combining financial analysis and market news.",
        add_datetime_to_instructions=True,
        show_tool_calls=True,
        markdown=True,
        enable_agentic_context=True,
        show_members_responses=False,
    )

    # Initialize FactChecker + Classifier + Router
    fact_checker = FactChecker(web_agent)
    classifier = QueryClassifier()
    router = QueryRouter({"web-agent": web_agent, "finance-agent": finance_agent}, fact_checker, classifier, agent_team)

    print("You are about to chat with the Finance Team!")
    if session_id is None:
        session_id = agent_team.session_id
        print(f"Started new Session: {session_id}\n")
    else:
        print(f"Continuing Session: {session_id}\n")

    # CLI loop
    while True:
        query = input("😎 User : ")
        if query.lower() in ["exit", "quit"]:
            print("👋 Exiting Finance Team.")
            break

        response = router.route(query)
        print(f"\n🧠 Response:\n{response}\n")


if __name__ == "__main__":
    typer.run(finance_team)

"""
💡 Example queries to explore:

1. "Compare the financial performance and recent news of AMZN, MSFT, and GOOGL."
2. "What’s the impact of recent Fed decisions on banking stocks like JPM and BAC?"
3. "Analyze the gaming industry outlook through ATVI, EA, and TTWO performance."
4. "How are META and SNAP performing after their recent earnings?"
5. "What’s the latest on AI chip manufacturers such as NVDA and AMD?"
6. "What is the impact of recent Donald Trump decisions to attack Venezuela on banking stocks?"  <-- triggers fact-check
"""
