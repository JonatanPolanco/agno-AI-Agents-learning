import streamlit as st
from multi_agent_team_market_finance_news import ValidationRouter, build_team, news_validator

st.title("💹 AI Team for Finance, Market and News Analysis")
st.write("Check the financial impact of events validated by news, market conditions, financial recommendations, and much more.")

query = st.text_area("Tu consulta", "Market impact of US military attack on Venezuelan cartels")

if st.button("Analizar"):
    team = build_team("user", None)
    router = ValidationRouter(team, news_validator)
    with st.spinner("Procesando..."):
        response = router.route(query)
    st.markdown(response)
