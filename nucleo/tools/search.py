"""Web search tool using Brave Search API."""

from typing import Any, Dict, List
import httpx

from .base import Tool


class SearchTool(Tool):
    """Web search using Brave Search API."""
    
    name = "search"
    description = "Search the web for current information"
    parameters = {
        'query': {
            'type': 'string',
            'description': 'The search query',
            'required': True
        },
        'count': {
            'type': 'integer',
            'description': 'Number of results to return (1-20)',
            'required': False
        }
    }
    
    async def execute(self, query: str, count: int = 5, **kwargs) -> Dict[str, Any]:
        """Execute web search.
        
        Args:
            query: Search query
            count: Number of results
            
        Returns:
            Search results
        """
        api_key = self.config.get('api_key')
        if not api_key:
            return {
                'success': False,
                'error': 'Search API key not configured'
            }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    'https://api.search.brave.com/res/v1/web/search',
                    headers={
                        'Accept': 'application/json',
                        'X-Subscription-Token': api_key
                    },
                    params={
                        'q': query,
                        'count': min(count, self.config.get('max_results', 5))
                    },
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    return {
                        'success': False,
                        'error': f'Search API error: {response.status_code}'
                    }
                
                data = response.json()
                results = self._parse_results(data)
                
                return {
                    'success': True,
                    'results': results,
                    'count': len(results)
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _parse_results(self, data: Dict) -> List[Dict[str, Any]]:
        """Parse Brave Search response.
        
        Args:
            data: Raw API response
            
        Returns:
            Parsed search results
        """
        results = []
        web_results = data.get('web', {}).get('results', [])
        
        for item in web_results:
            results.append({
                'title': item.get('title', ''),
                'url': item.get('url', ''),
                'description': item.get('description', ''),
            })
        
        return results
