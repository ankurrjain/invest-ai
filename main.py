"""
CLI entry point for InvestAI.
"""
import argparse
import sys
from invest_ai.agents.graph import run_research
from invest_ai.utils.ticker import resolve_ticker


def main():
    parser = argparse.ArgumentParser(description="InvestAI - Agentic Stock Research")
    parser.add_argument("--ticker", type=str, required=True, help="Stock ticker symbol (e.g., AAPL, RELIANCE)")
    parser.add_argument("--market", type=str, choices=["india", "us", "auto"], default="auto", help="Market to search in")
    parser.add_argument("--query", type=str, default="Provide a full investment research report.", help="Specific research query")

    args = parser.parse_args()

    ticker = resolve_ticker(args.ticker, args.market)
    print(f"Researching: {ticker} (Market: {args.market})")
    print(f"Query: {args.query}")
    print("-" * 50)
    print("Initiating agentic workflow...\n")

    try:
        result = run_research(ticker=ticker, market=args.market, query=args.query)
        
        print("\n" + "=" * 50)
        print("FINAL REPORT:")
        print("=" * 50)
        print(result.get("final_report", "No report generated."))
        
        print("\n" + "-" * 50)
        print(f"Agents Called: {', '.join(result.get('agents_called', []))}")
        
    except Exception as e:
        print(f"\nError running research: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
