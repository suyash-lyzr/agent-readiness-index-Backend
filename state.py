"""In-memory session state store."""
from typing import Dict, Any

# Global session store: session_id -> session dict
sessions: Dict[str, Any] = {}
