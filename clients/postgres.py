from typing import Any, Dict, List, Protocol, runtime_checkable


@runtime_checkable
class PostgresSearchClient(Protocol):
    async def get_candidate_ids(self, filters: Dict[str, Any]) -> List[int]:
        """Metadata + geospatial pre-filter returning internal asset IDs."""

    async def get_assets_by_ids(self, asset_ids: List[int]) -> List[Dict[str, Any]]:
        """Hydrate asset records for the IDs returned by Faiss."""


class InMemoryPostgresClient:
    """Lightweight stand-in for unit tests and local development."""

    def __init__(self, assets: Dict[int, Dict[str, Any]] | None = None):
        self.assets = assets or {}

    async def get_candidate_ids(self, filters: Dict[str, Any]) -> List[int]:
        if not self.assets:
            return []
        if not filters:
            return list(self.assets.keys())

        def matches(asset: Dict[str, Any]) -> bool:
            for key, value in filters.items():
                if asset.get(key) != value:
                    return False
            return True

        return [asset_id for asset_id, asset in self.assets.items() if matches(asset)]

    async def get_assets_by_ids(self, asset_ids: List[int]) -> List[Dict[str, Any]]:
        return [self.assets[asset_id] for asset_id in asset_ids if asset_id in self.assets]