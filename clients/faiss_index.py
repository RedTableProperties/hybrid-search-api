from typing import List, Tuple

import numpy as np


class InMemoryFaissIndex:
    """
    Deterministic in-memory vector index for tests.

    search_with_ids returns IDs sorted by descending dot-product similarity.
    """

    def __init__(self, vectors: dict[int, List[float]] | None = None):
        self.vectors = vectors or {}

    async def search_with_ids(
        self,
        query_vector: List[float],
        allowed_ids: np.ndarray,
        k: int,
        ef: int,
    ) -> Tuple[np.ndarray, np.ndarray]:
        del ef  # tuning knob; not needed for the in-memory implementation

        query = np.asarray(query_vector, dtype=np.float32)
        scored: list[tuple[float, int]] = []

        for asset_id in allowed_ids.tolist():
            vector = self.vectors.get(int(asset_id))
            if vector is None:
                continue
            score = float(np.dot(query, np.asarray(vector, dtype=np.float32)))
            scored.append((score, int(asset_id)))

        scored.sort(reverse=True)
        top = scored[:k]

        index_values = [item[1] for item in top]
        distance_values = [item[0] for item in top]
        while len(index_values) < k:
            index_values.append(-1)
            distance_values.append(-1.0)

        distances = np.array([distance_values], dtype=np.float32)
        indices = np.array([index_values], dtype=np.int64)
        return distances, indices