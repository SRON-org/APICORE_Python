from typing import Dict, Any

def parse_image(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse image configuration from response data."""
    return response_data.get('image', {})
