"""
Archivo: finance_team.py
------------------------
Define la lógica del equipo multi-agente de análisis financiero validado.
Incluye:
- Agentes individuales (validador, buscador web, analista financiero).
- Un equipo coordinado de agentes.
- Un enrutador que valida primero las noticias antes del análisis.
- Interfaz CLI para consultas interactivas.

Uso:
    python finance_team.py
"""

from typing import List, Optional
import typer
import os
import json
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google import Gemini
from agno.team.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools
from agno.storage.sqlite import SqliteStorage
from rich import print

# --- Importa prompts centralizados ---
from prompts import VALIDATOR_PROMPT, WEB_AGENT_PROMPT, FINANCE_AGENT_PROMPT, TEAM_PROMPT

load_dotenv()
team_storage = SqliteStorage(table_name="validated_finance_team", db_file="tmp/agents.db")

# --- Definición de Agentes ---
news_validator = Agent(
    name="News Validator",
    role="Fact-check and validate news claims before financial analysis",
    model=Gemini(
        id=os.environ.get("DEFAULT_MODEL", "gemini-2.5-pro"),
        api_key=os.environ.get("GOOGLE_API_KEY"),
    ),
    tools=[DuckDuckGoTools()],
    instructions=VALIDATOR_PROMPT,
    show_tool_calls=True,
    markdown=True,
)

web_agent = Agent(
    name="Web Agent",
    role="Search for latest financial news and market information",
    model=Gemini(
        id=os.environ.get("DEFAULT_MODEL", "gemini-2.5-pro"),
        api_key=os.environ.get("GOOGLE_API_KEY"),
    ),
    tools=[DuckDuckGoTools()],
    instructions=WEB_AGENT_PROMPT,
    show_tool_calls=True,
    markdown=True,
)

finance_agent = Agent(
    name="Finance Agent",
    role="Analyze financial data, metrics, market trends, and risk assessment",
    model=Gemini(
        id=os.environ.get("DEFAULT_MODEL", "gemini-2.5-pro"),
        api_key=os.environ.get("GOOGLE_API_KEY"),
    ),
    tools=[YFinanceTools(
        stock_price=True,
        analyst_recommendations=True,
        company_info=True,
        stock_fundamentals=True
    )],
    instructions=FINANCE_AGENT_PROMPT,
    show_tool_calls=True,
    markdown=True,
)


def build_team(user: str, session_id: Optional[str]) -> Team:
    """
    Crea un equipo coordinado de agentes para análisis financiero validado.
    """
    return Team(
        members=[web_agent, finance_agent],
        model=Gemini(
            id=os.environ.get("DEFAULT_MODEL", "gemini-2.5-pro"),
            api_key=os.environ.get("GOOGLE_API_KEY"),
        ),
        storage=team_storage,
        user_id=user,
        session_id=session_id,
        mode="coordinate",
        success_criteria="Deliver a comprehensive, fact-checked financial report with actionable insights.",
        instructions=TEAM_PROMPT,
        add_datetime_to_instructions=True,
        show_tool_calls=True,
        markdown=True,
        enable_agentic_context=True,
        show_members_responses=False,
    )


def safe_parse_json(text: str):
    """
    Intenta parsear JSON devuelto por un agente. Si falla, devuelve dict vacío.
    """
    try:
        return json.loads(text)
    except Exception:
        return {}


def present_response(team_response) -> str:
    """
    Da formato limpio y profesional a la respuesta final del equipo.
    Elimina duplicados accidentales.
    """
    text = getattr(team_response, "content", None) or (
        team_response.get("content") if isinstance(team_response, dict) else str(team_response)
    )
    text = text.strip()

    # Elimina duplicados exactos (cuando el bloque aparece dos veces)
    parts = text.split("\n\n")
    seen, cleaned = set(), []
    for p in parts:
        if p not in seen:
            cleaned.append(p)
            seen.add(p)
    return "\n\n".join(cleaned)


class ValidationRouter:
    """
    Enruta las consultas del usuario:
    1. Pasa primero por el validador de noticias.
    2. Con la información corregida, activa al equipo de análisis financiero.
    """

    def __init__(self, team: Team, validator: Agent):
        self.team = team
        self.validator = validator

    def route(self, query: str) -> str:
        print("Validating news claims...")
        validation_result = self.validator.run(
            f"Please fact-check this query and provide enhanced context in JSON: {query}"
        )
        print("Validation complete. Proceeding with analysis...")

        # Intentar parsear JSON del validador
        val_json = safe_parse_json(getattr(validation_result, "content", str(validation_result)))
        val_summary = val_json.get("summary", "")
        val_sources = val_json.get("sources", [])
        val_status = val_json.get("status", "uncertain")

        enhanced_prompt = f"""
        ORIGINAL USER QUERY: {query}

        FACT-CHECK STATUS: {val_status}
        FACT-CHECK SUMMARY: {val_summary}
        SOURCES: {val_sources}

        TEAM INSTRUCTIONS:
        Based on the validated context above, provide a comprehensive financial analysis.
        Use your own research + financial data, but do NOT repeat JSON blocks.
        Structure your response with clear sections and confidence indicators.
        """
        team_response = self.team.run(enhanced_prompt)
        return present_response(team_response)


def validated_finance_team(user: str = "user"):
    """
    CLI principal para interactuar con el equipo de agentes financieros validados.
    """
    session_id: Optional[str] = None
    new = typer.confirm("Do you want to start a new session?")
    if not new:
        existing_sessions: List[str] = team_storage.get_all_session_ids(user)
        if len(existing_sessions) > 0:
            # TODO: permitir elegir cuál cargar, por ahora la primera
            session_id = existing_sessions[0]

    agent_team = build_team(user, session_id)
    router = ValidationRouter(agent_team, news_validator)

    print("✅ Validated Finance Team Ready!")
    print("Features: News fact-checking + Financial analysis")

    if session_id is None:
        session_id = agent_team.session_id
        print(f"Started New Session: {session_id}\n")
    else:
        print(f"Continuing Session: {session_id}\n")

    print("💡 Example queries:")
    print("  • 'Impact of Tesla recall on stock price this week'")
    print("  • 'Fed rate hike rumors impact on tech stocks'")
    print("  • 'Nvidia AI chip shortage causing stock surge'")
    print("  • 'Apple earnings beat expectations last quarter'\n")

    while True:
        user_query = input("Ask the Validated Finance Team: ")
        if user_query.lower() in {"exit", "quit", "bye"}:
            print("👋 Thanks for using Validated Finance Team!")
            break
        if not user_query.strip():
            continue
        try:
            print(f"\n🔎 Processing: {user_query}")
            response = router.route(user_query)
            print(f"\n📑 **Complete Analysis:**\n{response}\n")
            print("-" * 60)
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            print("Please try again with a different query.\n")


if __name__ == "__main__":
    typer.run(validated_finance_team)
