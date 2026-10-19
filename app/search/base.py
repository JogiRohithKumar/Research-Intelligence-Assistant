"""
Abstract Search Provider Interface for Research Intelligence Assistant V2.
Decouples retrieval logic from specific external academic databases.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from app.models.domain import NormalizedPaper


class SearchProvider(ABC):
    """
    Abstract contract for scholarly and local search providers.
    Every provider must return canonical NormalizedPaper models.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider identifier (e.g. 'arxiv', 'local_corpus')."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if provider is configured and reachable."""
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[NormalizedPaper]:
        """
        Executes search against scholarly source and returns normalized papers.
        Must handle errors internally and return empty list on failure.
        """
        pass
