from typing import List, Optional

from pydantic import BaseModel, Field


class TransactionInput(BaseModel):
    raw_narrative: str = Field(..., description="Raw transaction narrative or counterparty description string from bank ledger")
    amount: float = Field(..., description="Transaction amount (negative for outflows/expenses, positive for inflows)")
    currency: str = Field(default="GBP", description="ISO-4217 3-letter currency code")
    booking_date: Optional[str] = Field(default=None, description="ISO-8601 date string (YYYY-MM-DD)")
    payment_rail: Optional[str] = Field(default=None, description="Optional payment rail hint: card, faster_payments, direct_debit, standing_order")
    mcc: Optional[str] = Field(default=None, description="Optional 4-digit Merchant Category Code")


class BatchEnrichRequest(BaseModel):
    transactions: List[TransactionInput] = Field(..., description="List of transactions to enrich (up to 100 per batch)")


class CleanMerchant(BaseModel):
    name: str = Field(..., description="Canonical cleaned human-readable merchant name")
    canonical_id: str = Field(..., description="Globally unique canonical merchant slug (e.g. mch_switch2_energy)")
    domain: Optional[str] = Field(default=None, description="Primary website domain of the merchant (e.g. switch2.co.uk)")
    logo_url: Optional[str] = Field(default=None, description="Clean logo icon URI")
    merchant_type: str = Field(..., description="Merchant business type (e.g. Energy Utility, Supermarket, SaaS, Transit, Dining)")
    country: str = Field(default="GB", description="Merchant home country (ISO-3166-1 alpha-2)")


class EnrichmentDetails(BaseModel):
    category_l1: str = Field(..., description="Primary Level-1 macro category")
    category_l2: str = Field(..., description="Level-2 subcategory")
    category_l3: str = Field(..., description="Level-3 fine-grained domain category")
    payment_channel: str = Field(..., description="Inferred payment channel (e.g. POS In-Store Contactless, Online Web Checkout, Direct Debit Mandate, Faster Payments TPP)")
    is_contractual_commitment: bool = Field(..., description="True if this represents a regular legally binding contract or utility obligation")
    confidence_score: float = Field(..., description="Classification confidence from 0.0 to 1.0")


class FiduciaryInsights(BaseModel):
    cadence: str = Field(..., description="Detected frequency: monthly, weekly, bi-weekly, annual, or discretionary_one_off")
    expected_amount_range: Optional[List[float]] = Field(default=None, description="Expected typical amount range [min, max]")
    is_essential_living_cost: bool = Field(..., description="True if essential for basic living (housing, utilities, groceries, council tax)")
    hmrc_tax_deductible: bool = Field(..., description="True if typically eligible as an allowable business/freelance expense under UK HMRC rules")
    tax_category: Optional[str] = Field(default=None, description="HMRC expense category (e.g. Office & Software Costs, Utilities, Travel & Subsistence, Non-Deductible Personal)")
    action_insight: str = Field(..., description="Actionable fiduciary commentary or alert for the user or financial manager")


class EnrichedTransaction(BaseModel):
    raw_narrative: str
    amount: float
    currency: str
    booking_date: Optional[str]
    clean_merchant: CleanMerchant
    enrichment: EnrichmentDetails
    fiduciary_insights: FiduciaryInsights
    source: str = Field(..., description="Execution path: 'deterministic_rule' | 'cache_hit' | 'smart_model'")


class BatchEnrichResponse(BaseModel):
    total_transactions: int
    enriched_transactions: List[EnrichedTransaction]
    cache_hits: int
    smart_model_hits: int
    processing_time_ms: float
