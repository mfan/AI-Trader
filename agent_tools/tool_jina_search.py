"""
Jina Search MCP Service - News and Web Search for Trading Decisions

This service provides web search and content scraping capabilities using Jina AI.
Useful for gathering news, market sentiment, and company information to inform trading decisions.

RESTORED: This service was previously removed but has been restored to provide
news search capabilities for the AI trading agent.
"""

from typing import Dict, Any, Optional, List
import os
import logging
import requests
from fastmcp import FastMCP
from dotenv import load_dotenv
import random
from datetime import datetime, timedelta
import re
import json
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.general_tools import get_config_value

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


def parse_date_to_standard(date_str: str) -> str:
    """
    Convert various date formats to standard format (YYYY-MM-DD HH:MM:SS)
    
    Args:
        date_str: Date string in various formats, such as "2025-10-01T08:19:28+00:00", 
                  "4 hours ago", "1 day ago", "May 31, 2025"
        
    Returns:
        Standard format datetime string, such as "2025-10-01 08:19:28"
    """
    if not date_str or date_str == 'unknown':
        return 'unknown'
    
    # Handle relative time formats
    if 'ago' in date_str.lower():
        try:
            now = datetime.now()
            if 'hour' in date_str.lower():
                hours = int(re.findall(r'\d+', date_str)[0])
                target_date = now - timedelta(hours=hours)
            elif 'day' in date_str.lower():
                days = int(re.findall(r'\d+', date_str)[0])
                target_date = now - timedelta(days=days)
            elif 'week' in date_str.lower():
                weeks = int(re.findall(r'\d+', date_str)[0])
                target_date = now - timedelta(weeks=weeks)
            elif 'month' in date_str.lower():
                months = int(re.findall(r'\d+', date_str)[0])
                target_date = now - timedelta(days=months * 30)  # Approximate handling
            else:
                return 'unknown'
            return target_date.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            pass
    
    # Handle ISO 8601 format, such as "2025-10-01T08:19:28+00:00"
    try:
        if 'T' in date_str and ('+' in date_str or 'Z' in date_str or date_str.endswith('00:00')):
            # Remove timezone information, keep only date and time part
            if '+' in date_str:
                date_part = date_str.split('+')[0]
            elif 'Z' in date_str:
                date_part = date_str.replace('Z', '')
            else:
                date_part = date_str
            
            # Parse ISO format
            if '.' in date_part:
                # Handle microseconds part, such as "2025-10-01T08:19:28.123456"
                parsed_date = datetime.strptime(date_part.split('.')[0], '%Y-%m-%dT%H:%M:%S')
            else:
                # Standard ISO format "2025-10-01T08:19:28"
                parsed_date = datetime.strptime(date_part, '%Y-%m-%dT%H:%M:%S')
            return parsed_date.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        pass
    
    # Handle other common formats
    try:
        # Handle "May 31, 2025" format
        if ',' in date_str and len(date_str.split()) >= 3:
            parsed_date = datetime.strptime(date_str, '%b %d, %Y')
            return parsed_date.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        pass
    
    try:
        # Handle "2025-10-01" format
        if re.match(r'\d{4}-\d{2}-\d{2}$', date_str):
            parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
            return parsed_date.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        pass
    
    # If unable to parse, return original string
    return date_str


class WebScrapingJinaTool:
    """
    Jina AI web search and scraping tool for market research and news gathering.
    """
    
    def __init__(self):
        self.api_key = os.environ.get("JINA_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Jina API key not provided! Please set JINA_API_KEY environment variable.\n"
                "Get your API key from: https://jina.ai/"
            )

    def __call__(self, query: str, max_results: int = 1) -> List[Dict[str, Any]]:
        """
        Search and scrape content for a query.
        
        Args:
            query: Search query (e.g., "Tesla earnings report", "NVDA stock news")
            max_results: Maximum number of URLs to scrape (default: 1)
        
        Returns:
            List of dictionaries containing scraped content
        """
        print(f"🔍 Searching for: {query}")
        all_urls = self._jina_search(query)
        return_content = []
        
        print(f"📄 Found {len(all_urls)} URLs")
        
        if len(all_urls) > max_results:
            # Randomly select from results
            all_urls = random.sample(all_urls, max_results)
        
        for url in all_urls:
            print(f"📥 Scraping: {url}")
            content = self._jina_scrape(url)
            return_content.append(content)
            print(f"✅ Scraped: {url}")

        return return_content  

    def _jina_scrape(self, url: str) -> Dict[str, Any]:
        """
        Scrape content from a URL using Jina Reader API.
        
        Args:
            url: URL to scrape
        
        Returns:
            Dictionary containing scraped content
        """
        try:
            jina_url = f'https://r.jina.ai/{url}'
            headers = {
                "Accept": "application/json",
                'Authorization': f'Bearer {self.api_key}',
                'X-Timeout': "10",
                "X-With-Generated-Alt": "true",
            }
            response = requests.get(jina_url, headers=headers)

            if response.status_code != 200:
                raise Exception(f"Jina AI Reader Failed for {url}: {response.status_code}")

            response_dict = response.json()

            return {
                'url': response_dict['data']['url'],
                'title': response_dict['data']['title'],
                'description': response_dict['data']['description'],
                'content': response_dict['data']['content'],
                'publish_time': response_dict['data'].get('publishedTime', 'unknown')
            }

        except Exception as e:
            logger.error(f"Scraping error for {url}: {e}")
            return {
                'url': url,
                'content': '',
                'error': str(e)
            }

    def _jina_search(self, query: str, num_results: int = 5) -> List[str]:
        """
        Search for URLs using Jina Search API.
        
        Args:
            query: Search query
            num_results: Number of results to return
        
        Returns:
            List of URLs
        """
        url = f'https://s.jina.ai/?q={query}&n={num_results}'
        headers = {
            'Authorization': f'Bearer {self.api_key}',        
            "Accept": "application/json",
            "X-Respond-With": "no-content"
        }
   
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            json_data = response.json()
            
            # Check if response data is valid
            if json_data is None:
                print(f"⚠️ Jina API returned empty data for query: {query}")
                return []
            
            if 'data' not in json_data:
                print(f"⚠️ Jina API response format abnormal for query: {query}")
                return []
            
            filtered_urls = []
            
            # Process search results, filter by date if TODAY_DATE is set
            today_date = get_config_value("TODAY_DATE")
            
            for item in json_data.get('data', []):
                if 'url' not in item:
                    continue
                    
                # Get publication date and convert to standard format
                raw_date = item.get('date', 'unknown')
                standardized_date = parse_date_to_standard(raw_date)
                
                # If unable to parse date or TODAY_DATE not set, keep result
                if not today_date or standardized_date == 'unknown' or standardized_date == raw_date:
                    filtered_urls.append(item['url'])
                    continue
                
                # Check if before TODAY_DATE (for backtesting)
                if standardized_date < today_date:
                    filtered_urls.append(item['url'])
            
            print(f"🔍 Found {len(filtered_urls)} URLs after date filtering")
            return filtered_urls
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Jina API request failed: {e}")
            return []
        except ValueError as e:
            print(f"❌ Jina API response parsing failed: {e}")
            return []
        except Exception as e:
            print(f"❌ Jina search unknown error: {e}")
            return []


# Initialize FastMCP server
mcp = FastMCP("Jina Search")


@mcp.tool()
def search_news(query: Optional[str] = None, max_results: int = 1, symbol: Optional[str] = None) -> str:
    """
    Search for news and web content related to stocks, companies, or market events.
    
    Use this tool to gather recent news, earnings reports, market sentiment, and other
    information that could inform trading decisions.
    
    Examples:
    - search_news("Tesla earnings report Q3 2025")
    - search_news("NVDA stock price news")
    - search_news("Federal Reserve interest rate decision")
    - search_news("Apple iPhone sales")
    - search_news(symbol="AAPL", max_results=3)
    
    Args:
        query: Search query describing the information you need
        max_results: Maximum number of articles to retrieve (default: 1, max: 3)
        symbol: Optional stock ticker; falls back to "<symbol> stock news" when query is omitted
    
    Returns:
        Formatted string containing article content including:
        - URL: Original web page link
        - Title: Article title
        - Description: Brief description
        - Publish Time: Publication date (if available)
        - Content: Main article text (truncated for readability)
    """
    try:
        if query is None:
            if symbol:
                query = f"{symbol} stock news"
            else:
                return "⚠️ search_news requires either a 'query' string or a 'symbol'."

        if isinstance(query, str):
            query = query.strip()
        else:
            query = str(query)

        if not query:
            return "⚠️ search_news received an empty query; please provide a topic or symbol."

        try:
            max_results = int(max_results)
        except (TypeError, ValueError):
            max_results = 1

        max_results = min(max(1, max_results), 3)
        
        tool = WebScrapingJinaTool()
        results = tool(query, max_results=max_results)
        
        # Check if results are empty
        if not results:
            return f"⚠️ Search query '{query}' found no results. This may be due to network issues or API limitations."
        
        # Format results
        formatted_results = []
        for i, result in enumerate(results, 1):
            if 'error' in result:
                formatted_results.append(f"❌ Article {i} Error: {result['error']}")
            else:
                # Truncate content for readability
                content = result['content'][:2000] if result['content'] else "No content available"
                
                formatted_results.append(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📰 Article {i}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 URL: {result['url']}
📌 Title: {result['title']}
📝 Description: {result['description']}
📅 Published: {result['publish_time']}

📄 Content:
{content}
{'...' if len(result.get('content', '')) > 2000 else ''}
""")
        
        if not formatted_results:
            return f"⚠️ Search query '{query}' returned empty results."
        
        return "\n".join(formatted_results)
        
    except Exception as e:
        return f"❌ Search tool execution failed: {str(e)}"


@mcp.tool()
def get_company_info(symbol: str) -> str:
    """
    Get recent company information and news for a stock symbol.
    
    This is a convenience wrapper around search_news that formats the query
    specifically for company/stock information.
    
    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "TSLA", "NVDA")
    
    Returns:
        Formatted news and company information
    """
    query = f"{symbol} stock news company information latest"
    return search_news(query, max_results=1)


if __name__ == "__main__":
    """
    Run Jina Search MCP service with HTTP transport.
    Port can be configured via SEARCH_HTTP_PORT environment variable.
    """
    port = int(os.getenv("SEARCH_HTTP_PORT", "8001"))
    
    print("=" * 60)
    print("🔍 Starting Jina Search MCP Service")
    print("=" * 60)
    print(f"📡 Transport: streamable-http")
    print(f"🔌 Port: {port}")
    print(f"🌐 Endpoint: http://localhost:{port}/mcp")
    print("=" * 60)
    print(f"✅ Service ready - providing news search for trading decisions")
    print("=" * 60)
    
    mcp.run(transport="streamable-http", port=port)
