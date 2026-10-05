"""
Fiduciary Financial Enrichment & Intelligence Engine.
Autonomous, multi-tier transaction enrichment powered by deterministic rules,
cached canonical merchant registries, and frontier smart models (Gemini 2.5 Flash).
"""

from fiduciary.enrichment.engine import EnrichmentEngine
from fiduciary.enrichment.models import (
    BatchEnrichRequest,
    BatchEnrichResponse,
    CleanMerchant,
    EnrichedTransaction,
    EnrichmentDetails,
    FiduciaryInsights,
    TransactionInput,
)

__all__ = [
    "EnrichmentEngine",
    "TransactionInput",
    "BatchEnrichRequest",
    "CleanMerchant",
    "EnrichmentDetails",
    "FiduciaryInsights",
    "EnrichedTransaction",
    "BatchEnrichResponse",
]
