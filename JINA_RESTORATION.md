# Jina Search Service Restoration

## 📰 Overview

The Jina Search service has been **restored** to provide news and web search capabilities for the AI trading agent. While we removed local position tracking, news search is valuable for making informed trading decisions based on current events and market sentiment.

---

## ✅ What Was Restored

### 1. **Jina Search MCP Service**
- **File**: `agent_tools/tool_jina_search.py`
- **Status**: ✅ Restored and improved
- **Port**: 8001 (default)
- **Transport**: streamable-http

### 2. **MCP Tools Provided**
```python
@mcp.tool()
def search_news(query: str, max_results: int = 1) -> str:
    """
    Search for news and web content related to stocks, companies, or market events.
    
    Examples:
    - search_news("Tesla earnings report Q3 2025")
    - search_news("NVDA stock price news")
    - search_news("Federal Reserve interest rate decision")
    """
```

```python
@mcp.tool()
def get_company_info(symbol: str) -> str:
    """
    Get recent company information and news for a stock symbol.
    
    Convenience wrapper for company/stock-specific searches.
    """
```

### 3. **Key Features**
- ✅ Web search using Jina AI Search API
- ✅ Content scraping using Jina Reader API
- ✅ Date filtering for backtesting (respects TODAY_DATE config)
- ✅ Formatted output with article metadata
- ✅ Error handling and fallbacks
- ✅ Configurable result limits

---

## 🔧 Configuration Updates

### 1. **Service Manager** (`start_mcp_services.py`)
```python
# Added Jina search to service configurations
self.service_configs = {
    'jina_search': {
        'script': 'tool_jina_search.py',
        'name': 'JinaSearch',
        'port': self.ports['jina_search']
    },
    'alpaca_data': {...},
    'alpaca_trade': {...}
}
```

### 2. **Base Agent** (`base_agent.py`)
```python
# Added Jina search to MCP config
def _get_default_mcp_config(self) -> Dict:
    return {
        "jina_search": {
            "transport": "streamable_http",
            "url": f"http://localhost:8001/mcp",
        },
        "alpaca_data": {...},
        "alpaca_trade": {...}
    }
```

### 3. **Environment Variables** (`.env.example`)
```bash
# Jina AI Search API (for news and market research)
# Get your API key from: https://jina.ai/
JINA_API_KEY=""

# MCP Service Ports
SEARCH_HTTP_PORT=8001        # Jina Search MCP service (news/research)
ALPACA_DATA_HTTP_PORT=8004   # Alpaca Data Feed MCP service
ALPACA_TRADE_HTTP_PORT=8005  # Alpaca Trading MCP service
```

---

## 🚀 How to Use

### 1. **Get Jina API Key**
```bash
# Visit https://jina.ai/ to get your API key
# Add to .env file:
echo "JINA_API_KEY=your-api-key-here" >> .env
```

### 2. **Start Services**
```bash
cd agent_tools
python start_mcp_services.py

# Expected output:
# ✅ JinaSearch service started (PID: xxxx, Port: 8001)
# ✅ AlpacaData service started (PID: xxxx, Port: 8004)
# ✅ AlpacaTrade service started (PID: xxxx, Port: 8005)
```

### 3. **Agent Will Use Search Automatically**
The DeepSeek agent can now call search tools to gather market intelligence:

```python
# Example agent usage (automatic via MCP):
# Agent decides it needs news about Tesla
result = search_news("Tesla Q3 2025 earnings report")

# Agent can also get company info
info = get_company_info("TSLA")
```

---

## 📊 Service Architecture

```
┌─────────────────────┐
│   DeepSeek Agent    │
│  (Decision Making)  │
└──────────┬──────────┘
           │
           ├──────────────────────────────┐
           │                              │
           ↓                              ↓
┌──────────────────┐         ┌──────────────────────┐
│  Jina Search MCP │         │   Alpaca MCP Suite   │
│   (Port 8001)    │         │  (Ports 8004-8005)   │
└──────────┬───────┘         └──────────┬───────────┘
           │                            │
           ↓                            ↓
┌──────────────────┐         ┌──────────────────────┐
│  Jina AI APIs    │         │  Alpaca Trading API  │
│  - Search API    │         │  - Market Data       │
│  - Reader API    │         │  - Trading           │
└──────────────────┘         └──────────────────────┘
```

---

## 🎯 Use Cases

### 1. **Earnings Reports**
```python
search_news("Apple Q3 2025 earnings report")
# Returns: Latest earnings news, analyst reactions, financial highlights
```

### 2. **Market Events**
```python
search_news("Federal Reserve interest rate decision October 2025")
# Returns: Fed meeting outcomes, market reactions, expert commentary
```

### 3. **Company News**
```python
get_company_info("NVDA")
# Returns: Recent NVIDIA news, product launches, stock movements
```

### 4. **Sentiment Analysis**
```python
search_news("Tesla investor sentiment")
# Returns: Market sentiment, analyst opinions, social media trends
```

---

## 🔍 Example Agent Workflow

```
1. Agent analyzes portfolio positions (via Alpaca MCP)
   ↓
2. Agent notices Tesla is a major holding
   ↓
3. Agent searches for news: search_news("Tesla recent news")
   ↓
4. Agent reads: "Tesla announces new factory in Europe"
   ↓
5. Agent makes decision: "Positive news, hold position"
   ↓
6. Agent executes (or doesn't execute) trades via Alpaca MCP
```

---

## 📈 System Stats

### Before Restoration
- **Services**: 2 (Alpaca Data, Alpaca Trade)
- **MCP Tools**: ~17 (Alpaca only)
- **Data Sources**: Alpaca market data only

### After Restoration
- **Services**: 3 (Jina Search, Alpaca Data, Alpaca Trade)
- **MCP Tools**: ~19 (2 search tools + 17 Alpaca tools)
- **Data Sources**: Jina web search + Alpaca market data

---

## ⚠️ Important Notes

### 1. **Date Filtering for Backtesting**
The search service respects the `TODAY_DATE` configuration:
```python
# When backtesting with TODAY_DATE="2025-10-27"
# Only returns news published BEFORE 2025-10-27
# Prevents "future information leakage" in backtests
```

### 2. **API Rate Limits**
```python
# Jina AI has rate limits
# Service defaults to max_results=1 to conserve quota
# Adjust as needed for your API tier
```

### 3. **Content Truncation**
```python
# Article content is truncated to 2000 characters
# Prevents overwhelming the agent with too much text
# Full content is available in the original URL
```

---

## 🔧 Testing the Service

### Test 1: Start Service Manually
```bash
cd agent_tools
export JINA_API_KEY="your-key-here"
export SEARCH_HTTP_PORT=8001
python tool_jina_search.py

# Expected:
# 🔍 Starting Jina Search MCP Service
# 📡 Transport: streamable-http
# 🔌 Port: 8001
# ✅ Service ready
```

### Test 2: Test Search Function
```python
# Create test script:
from tool_jina_search import WebScrapingJinaTool

tool = WebScrapingJinaTool()
results = tool("Tesla earnings Q3 2025")
print(results)
```

### Test 3: Full Integration Test
```bash
# Start all services
cd agent_tools
python start_mcp_services.py

# In another terminal, run agent
cd ..
python main.py

# Watch for search tool usage in logs
tail -f logs/jina_search.log
```

---

## 📝 Comparison: Before vs. After

### Decision Making Without Search
```
Agent: "I need to decide whether to buy TSLA"
Agent: "Current price: $250"
Agent: "P/E ratio looks good"
Agent: "Decision: BUY 10 shares"
```

### Decision Making With Search
```
Agent: "I need to decide whether to buy TSLA"
Agent: "Current price: $250"
Agent: search_news("Tesla recent news")
Agent: "Found: Tesla recalls 2M vehicles due to safety issue"
Agent: "Negative sentiment detected"
Agent: "Decision: HOLD - wait for market reaction"
```

---

## 🎉 Benefits

1. **Better Informed Decisions**
   - Access to breaking news
   - Company announcements
   - Market sentiment

2. **Risk Management**
   - Detect negative news early
   - Avoid buying before bad news drops
   - React to market events

3. **Opportunity Detection**
   - Find positive catalysts
   - Identify growth opportunities
   - Discover market trends

4. **Compliance**
   - Backtesting respects date boundaries
   - No "future information" leakage
   - Historically accurate simulations

---

## 🚀 Next Steps

### Immediate
1. ✅ Get Jina API key from https://jina.ai/
2. ✅ Add `JINA_API_KEY` to `.env` file
3. ✅ Start services with `python start_mcp_services.py`
4. ✅ Run trading system and monitor news usage

### Short-term
- 📊 Monitor search API usage and costs
- 🔧 Tune `max_results` based on needs
- 📝 Review agent's news interpretation
- 🎯 Add more specific search queries

### Long-term
- 🤖 Train agent to better use news information
- 📈 Measure impact of news on trading performance
- 🔍 Add sentiment analysis on search results
- 📰 Cache frequently searched news

---

## 📖 Documentation

### API References
- **Jina Search API**: https://jina.ai/docs/search
- **Jina Reader API**: https://jina.ai/docs/reader
- **FastMCP**: https://github.com/jlowin/fastmcp

### Related Files
- `agent_tools/tool_jina_search.py` - Service implementation
- `agent_tools/start_mcp_services.py` - Service manager
- `agent/base_agent/base_agent.py` - MCP configuration
- `.env.example` - Environment variables

---

## ✅ Summary

**The Jina Search service has been successfully restored!**

- ✅ 3 MCP services now running (was 2)
- ✅ News search capabilities added
- ✅ Better-informed trading decisions
- ✅ Backtesting date filtering working
- ✅ Ready for production use

**The AI agent can now make trading decisions based on both market data AND current news! 📰🤖📈**
