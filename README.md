\# InvestAI 📈



InvestAI is an \*\*Agentic Stock Research Platform\*\* built with \[LangGraph](https://python.langchain.com/docs/langgraph) and \[Streamlit](https://streamlit.io/). It utilizes a multi-agent AI architecture to perform deep fundamental, technical, and thematic research on both \*\*US and Indian stock markets\*\*.



Powered by local LLMs via \[Ollama](https://ollama.com/) (or cloud models) and real-time financial data from `yfinance` and DuckDuckGo search, InvestAI works as your personal team of specialized financial analysts.



\---



\## 🚀 Features



\### 1. Single Stock Deep Dives

Analyze any specific stock in detail. The Supervisor agent dynamically routes your query to the right specialist agents:

\- \*\*Technical Analysis\*\*: Moving averages, RSI, MACD, Bollinger Bands, and volume analysis.

\- \*\*Fundamental Analysis\*\*: Valuation metrics, income statements, balance sheets, and cash flow.

\- \*\*News \& Sentiment\*\*: Latest headlines, market sentiment, and upcoming catalysts.

\- \*\*Dividend Yield Report\*\*: Detailed analysis of dividend safety, payout ratios, and growth history.

\- \*\*Economic Moat Report\*\*: Evaluation of durable competitive advantages, ROIC, and margins.



\### 2. Compare Stocks

Input a comma-separated list of tickers (e.g., `AAPL, MSFT, GOOGL`). The \*\*Comparison Agent\*\* will generate a side-by-side analysis of valuation, performance, and financial health, ultimately declaring a winner.



\### 3. Thematic Screener

Looking for ideas? Enter a theme (e.g., \*"AI Semiconductors"\* or \*"Renewable Energy in India"\*). The \*\*Screener Agent\*\* will search the web for relevant companies, evaluate their economic moats and technical entry points, and present a ranked list of top picks.



\---



\## 🏗️ Architecture



InvestAI uses a \*\*Supervisor-Worker\*\* graph architecture orchestrated by LangGraph:

1\. \*\*Supervisor Node\*\*: Understands the UI state and user query. Routes the task to the appropriate specialist agents (or directly to Comparison/Screener).

2\. \*\*Specialist Agents\*\* (`technical.py`, `fundamental.py`, `news.py`, `dividend.py`, `moat.py`, `comparison.py`, `screener.py`): ReAct agents equipped with custom Python tools to fetch real-time market data.

3\. \*\*Synthesizer Node\*\*: Gathers all specialist findings and drafts a cohesive, professional markdown research report.



\---



\## 🛠️ Setup \& Installation



This project uses `uv` for lightning-fast dependency management.



1\. \*\*Clone the repository:\*\*

&#x20;  ```bash

&#x20;  git clone https://github.com/yourusername/invest-ai.git

&#x20;  cd invest-ai

&#x20;  ```



2\. \*\*Install dependencies using `uv`:\*\*

&#x20;  ```bash

&#x20;  uv sync

&#x20;  ```



3\. \*\*Configure Environment Variables:\*\*

&#x20;  Copy the example environment file and update your preferred LLM model.

&#x20;  ```bash

&#x20;  cp .env.example .env

&#x20;  ```

&#x20;  \*Note: Ensure `MODEL\_NAME` matches a model you have pulled in Ollama (e.g., `llama3`, `qwen2.5:3b`, or `nemotron-3-super:cloud`).\*



4\. \*\*Start Ollama (If using local models):\*\*

&#x20;  Ensure your Ollama server is running in the background.

&#x20;  ```bash

&#x20;  ollama serve

&#x20;  ```



\---



\## 💻 Usage



\### Streamlit Web App (Recommended)

The primary way to interact with InvestAI is through its beautiful Streamlit UI.

```bash

uv run streamlit run app.py

```

This will open the app in your browser at `http://localhost:8501`. 

\- Select your target market (US or India).

\- Choose your Mode: Single Stock, Compare Stocks, or Thematic Screener.

\- Hit \*\*Run Agentic Research\*\*!



\### Command Line Interface (CLI)

You can also run quick single-stock deep dives directly from your terminal:

```bash

uv run main.py --ticker AAPL --market us

uv run main.py --ticker RELIANCE --market india

```



\---



\## 🌍 Supported Markets

\- \*\*US Markets (NYSE/NASDAQ)\*\*: Enter standard tickers (e.g., `AAPL`, `TSLA`).

\- \*\*Indian Markets (NSE/BSE)\*\*: Enter the ticker name (e.g., `RELIANCE`, `TCS`). The app will automatically append `.NS` for Yahoo Finance compatibility.



\---

\*Disclaimer: InvestAI provides AI-generated research for informational purposes only. It is not financial advice. Always do your own due diligence before making investment decisions.\*



