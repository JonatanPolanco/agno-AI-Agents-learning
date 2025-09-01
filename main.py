"""
🗞️ Multi-Agent Finance & News Team with Smart Validation
--------------------------------------------------------
This project demonstrates a professional multi-agent system with an intelligent
news validation layer that fact-checks queries before analysis.

Team members:
1. News Validator → Fact-checks and validates news claims before analysis
2. Web Agent      → Searches the web for latest credible news  
3. Finance Agent  → Analyzes financial data and market trends
4. Lead Editor    → Coordinates and synthesizes insights into final report

Pipeline:
- User query → News Validator (fact-check) → Enhanced context → Team Analysis
- Validator corrects misinformation and provides accurate context
- Team delivers fact-checked, data-driven financial insights

Example queries:
1. "Compare the financial performance and recent news of AMZN, MSFT, and GOOGL"
2. "What's the impact of recent Fed decisions on banking stocks? Focus on JPM and BAC" 
3. "Impact of Trump attacking Venezuela on banking stocks" → Gets corrected by validator
4. "Tesla recall affecting stock price" → Validator verifies if recall actually happened
5. "Nvidia AI chip shortage rumors" → Validator separates fact from speculation
"""

from typing import List, Optional
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

# Load environment
load_dotenv()

# Persistent storage
team_storage = SqliteStorage(table_name="validated_finance_team", db_file="tmp/agents.db")

# === News Validation Agent ===
news_validator = Agent(
    name="News Validator",
    role="Fact-check and validate news claims before financial analysis",
    model=Gemini(
        id=os.environ.get("DEFAULT_MODEL", "gemini-1.5-flash"),
        api_key=os.environ.get("GOOGLE_API_KEY"),
    ),
    tools=[DuckDuckGoTools()],
    instructions="""
    You are a expert fact-checker specializing in financial and political news validation.
    Your job is to verify claims and provide accurate context before financial analysis begins.

    VALIDATION PROCESS:
    1. IDENTIFY key factual claims in the user query
    2. SEARCH for recent credible sources to verify each claim
    3. DISTINGUISH between verified facts, partial truths, and misinformation
    4. CORRECT any inaccuracies with precise, factual information
    5. PROVIDE enhanced context with proper framing

    SOURCE HIERARCHY:
    - TIER 1: Reuters, Bloomberg, AP News, BBC, WSJ, official government sources
    - TIER 2: CNN, NBC, CBS, ABC, major newspapers
    - TIER 3: Specialized financial media (CNBC, MarketWatch)
    - AVOID: Social media, unverified blogs, partisan sources

    OUTPUT FORMAT:
    **FACT-CHECK SUMMARY:**
    - Original Claim: [user's claim]
    - Verification Status: VERIFIED / PARTIALLY TRUE / FALSE / UNCLEAR
    - Accurate Context: [corrected/enhanced version]
    - Source Quality: HIGH/MEDIUM/LOW confidence
    - Recommendation: [how to proceed with analysis]

    **ENHANCED QUERY FOR ANALYSIS:**
    [Provide corrected query with proper context for the finance team]

    EXAMPLES:
    - "Trump attacking Venezuela" → Verify actual US actions vs Venezuela
    - "Tesla recall" → Confirm if recall actually happened, scope, timeline
    - "Fed rate hike rumors" → Distinguish official communications from speculation
    - "Company bankruptcy rumors" → Verify financial status vs social media claims
    """,
    show_tool_calls=True,
    markdown=True,
)

# === Web Research Agent ===
web_agent = Agent(
    name="Web Agent",
    role="Search for latest credible financial news and market information",
    model=Gemini(
        id=os.environ.get("DEFAULT_MODEL", "gemini-1.5-flash"),
        api_key=os.environ.get("GOOGLE_API_KEY"),
    ),
    tools=[DuckDuckGoTools()],
    instructions="""
    You are a skilled financial news researcher specializing in market-moving information.
    
    Focus on:
    - Recent credible financial news from trusted sources
    - Market reactions and investor sentiment
    - Corporate announcements and earnings
    - Economic policy impacts and regulatory changes
    - Geopolitical events affecting financial markets
    
    Prioritize sources like Reuters, Bloomberg, WSJ, Financial Times, SEC filings.
    Always note the recency and credibility of your sources.
    """,
    show_tool_calls=True,
    markdown=True,
)

# === Financial Data Agent ===
finance_agent = Agent(
    name="Finance Agent",
    role="Analyze financial data, metrics, and market trends",
    model=Gemini(
        id=os.environ.get("DEFAULT_MODEL", "gemini-1.5-flash"),
        api_key=os.environ.get("GOOGLE_API_KEY"),
    ),
    tools=[YFinanceTools(
        stock_price=True, 
        analyst_recommendations=True, 
        company_info=True,
        stock_fundamentals=True
    )],
    instructions="""
    You are a quantitative financial analyst providing data-driven insights.
    
    Provide:
    - Current stock prices, performance, and volatility metrics
    - Financial ratios and fundamental analysis
    - Analyst recommendations and price targets
    - Historical performance context and trends
    - Risk assessment based on financial indicators
    - Sector and peer comparisons where relevant
    
    Always include specific numbers, dates, and data sources.
    Contextualize current performance within broader market trends.
    """,
    show_tool_calls=True,
    markdown=True,
)

# === Enhanced Router with Validation ===
class ValidationRouter:
    """
    Routes queries through news validation before sending to analysis team
    """
    
    def __init__(self, team: Team, validator: Agent):
        self.team = team
        self.validator = validator
        
    def route(self, query: str) -> str:
        """
        Process query through validation pipeline then team analysis
        """
        print("🔍 Validating news claims...")
        
        # Step 1: Validate the query
        validation_result = self.validator.run(
            f"Please fact-check this query and provide enhanced context: {query}"
        )
        
        print("✅ Validation complete. Proceeding with analysis...")
        
        # Step 2: Send validated context to team
        enhanced_prompt = f"""
        ORIGINAL USER QUERY: {query}
        
        VALIDATION RESULTS:
        {validation_result}
        
        TEAM INSTRUCTIONS:
        Based on the fact-check results above, provide comprehensive financial analysis.
        Use the enhanced/corrected context from the validator to ensure accuracy.
        Combine recent news research with concrete financial data and metrics.
        Structure your response with clear sections and confidence indicators.
        """
        
        return self.team.run(enhanced_prompt)

# === Main Function ===
def validated_finance_team(user: str = "user"):
    """
    Interactive finance team with built-in news validation
    """
    session_id: Optional[str] = None
    
    # Session management
    new = typer.confirm("Do you want to start a new session?")
    if not new:
        existing_sessions: List[str] = team_storage.get_all_session_ids(user)
        if len(existing_sessions) > 0:
            session_id = existing_sessions[0]
    
    # Create the analysis team
    agent_team = Team(
        members=[web_agent, finance_agent],
        model=Gemini(
            id=os.environ.get("DEFAULT_MODEL", "gemini-1.5-flash"),
            api_key=os.environ.get("GOOGLE_API_KEY"),
        ),
        storage=team_storage,
        user_id=user,
        session_id=session_id,
        mode="coordinate",
        success_criteria="""
        Deliver a comprehensive, fact-checked financial report that includes:
        1. Verification of key claims and accurate context
        2. Recent credible news and market analysis  
        3. Current financial data and performance metrics
        4. Clear risk assessment and confidence indicators
        5. Actionable insights based on verified information
        """,
        instructions="""
        You are the Lead Editor coordinating a fact-checked financial analysis team.
        
        Your responsibilities:
        1. Synthesize validated news context with current financial data
        2. Ensure all analysis is based on verified, credible information
        3. Provide clear confidence indicators for different aspects of the analysis
        4. Structure reports with proper disclaimers based on information certainty
        5. Deliver actionable insights appropriate for the validated context
        
        Always acknowledge when claims have been corrected by the validator
        and explain how this affects the financial analysis.
        """,
        add_datetime_to_instructions=True,
        show_tool_calls=True,
        markdown=True,
        enable_agentic_context=True,
        show_members_responses=False,
    )
    
    # Create validation router
    router = ValidationRouter(agent_team, news_validator)
    
    # Welcome messages
    print("🚀 Validated Finance Team Ready!")
    print("📋 Features: News fact-checking + Financial analysis")
    
    if session_id is None:
        session_id = agent_team.session_id
        print(f"📝 Started New Session: {session_id}\n")
    else:
        print(f"📂 Continuing Session: {session_id}\n")
    
    print("💡 Example queries:")
    print("  • 'Impact of Trump attacking Venezuela on banking stocks'")
    print("  • 'Tesla recall affecting stock price this week'") 
    print("  • 'Fed rate hike rumors impact on tech stocks'")
    print("  • 'Nvidia AI chip shortage causing stock surge'")
    print("  • 'Apple earnings beat expectations last quarter'\n")
    
    # Interactive loop
    while True:
        user_query = input("💰 Ask the Validated Finance Team: ")
        if user_query.lower() in {"exit", "quit", "bye"}:
            print("👋 Thanks for using Validated Finance Team!")
            break
        
        if not user_query.strip():
            continue
            
        try:
            print(f"\n📊 Processing: {user_query}")
            response = router.route(user_query)
            print(f"\n📈 **Complete Analysis:**\n{response}\n")
            print("-" * 60)
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            print("Please try again with a different query.\n")

if __name__ == "__main__":
    typer.run(validated_finance_team)

# === Usage Examples ===
"""
EXAMPLE INTERACTIONS:

Query: "What is the impact of Trump attacking Venezuela on banking stocks?"

News Validator Output:
**FACT-CHECK SUMMARY:**
- Original Claim: "Trump attacking Venezuela"  
- Verification Status: PARTIALLY TRUE
- Accurate Context: US has deployed naval assets and military advisors to combat 
  drug cartels, but this is not a direct "attack on Venezuela" as a sovereign nation
- Source Quality: HIGH confidence (Reuters, AP News, Defense Department)
- Recommendation: Analyze geopolitical risk impact with corrected framing

**ENHANCED QUERY FOR ANALYSIS:**
"What is the impact of recent US military deployment to combat Venezuelan drug 
cartels on banking stocks, particularly those with Latin American exposure?"

Then the finance team analyzes based on the corrected, factual context.

---

Query: "Tesla stock dropping due to massive recall"

News Validator Output:
**FACT-CHECK SUMMARY:**
- Original Claim: "Tesla massive recall"
- Verification Status: NEEDS VERIFICATION
- Accurate Context: No major Tesla recall announced in past 30 days. Last significant 
  recall was [specific details from search]
- Source Quality: MEDIUM confidence
- Recommendation: Analyze based on actual Tesla news, not unverified recall claims

This prevents the team from analyzing based on false premises!
"""