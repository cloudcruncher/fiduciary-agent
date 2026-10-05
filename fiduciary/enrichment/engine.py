import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from fiduciary.enrichment.models import (
    BatchEnrichResponse,
    CleanMerchant,
    EnrichedTransaction,
    EnrichmentDetails,
    FiduciaryInsights,
    TransactionInput,
)
from fiduciary.storage.db import (
    get_cached_enrichment,
    save_cached_enrichment,
)

logger = logging.getLogger(__name__)


class EnrichmentEngine:
    """
    Autonomous Financial Transaction Enrichment & Intelligence Engine.
    3-Tier Architecture:
    1. Deterministic narrative cleaning + Pre-seeded UK Merchant Knowledge Base (<1ms)
    2. High-performance SQLite Canonical Merchant Cache (<1ms)
    3. Frontier Smart Model (Gemini 2.5 Flash / LLMClient) for long-tail disambiguation & semantic reasoning
    """

    # Comprehensive curated registry of UK & Global counterparties
    PRESEEDED_KNOWLEDGE_BASE: Dict[str, Dict[str, Any]] = {
        "switch2_energy": {
            "name": "Switch2 Energy",
            "domain": "switch2.co.uk",
            "merchant_type": "District Energy Utility",
            "category_l1": "Utilities & Housing",
            "category_l2": "Energy & Heating",
            "category_l3": "District Community Heating",
            "is_contractual_commitment": True,
            "is_essential_living_cost": True,
            "hmrc_tax_deductible": False,
            "tax_category": "Non-Deductible Personal Living",
            "cadence": "monthly",
            "action_insight": "Essential district heating utility. Direct payment via communal energy provider."
        },
        "thames_water": {
            "name": "Thames Water",
            "domain": "thameswater.co.uk",
            "merchant_type": "Water Utility",
            "category_l1": "Utilities & Housing",
            "category_l2": "Water & Drainage",
            "category_l3": "Residential Water Supply",
            "is_contractual_commitment": True,
            "is_essential_living_cost": True,
            "hmrc_tax_deductible": False,
            "tax_category": "Non-Deductible Personal Living",
            "cadence": "monthly",
            "action_insight": "Essential water supply commitment. Direct Debit mandate active."
        },
        "british_gas": {
            "name": "British Gas",
            "domain": "britishgas.co.uk",
            "merchant_type": "Energy Utility",
            "category_l1": "Utilities & Housing",
            "category_l2": "Gas & Electricity",
            "category_l3": "Dual Fuel Household Energy",
            "is_contractual_commitment": True,
            "is_essential_living_cost": True,
            "hmrc_tax_deductible": False,
            "tax_category": "Non-Deductible Personal Living",
            "cadence": "monthly",
            "action_insight": "Standard domestic energy bill. Verified monthly billing schedule."
        },
        "lb_hounslow": {
            "name": "London Borough of Hounslow",
            "domain": "hounslow.gov.uk",
            "merchant_type": "Local Authority / Municipal Council",
            "category_l1": "Utilities & Housing",
            "category_l2": "Council & Municipal",
            "category_l3": "UK Council Tax",
            "is_contractual_commitment": True,
            "is_essential_living_cost": True,
            "hmrc_tax_deductible": False,
            "tax_category": "Non-Deductible Personal Living",
            "cadence": "monthly",
            "action_insight": "Statutory UK Council Tax obligation. Essential local government precept."
        },
        "tv_licence": {
            "name": "TV Licensing",
            "domain": "tvlicensing.co.uk",
            "merchant_type": "Statutory Broadcast Authority",
            "category_l1": "Utilities & Housing",
            "category_l2": "Broadcast & Media Licensing",
            "category_l3": "BBC TV Licence",
            "is_contractual_commitment": True,
            "is_essential_living_cost": False,
            "hmrc_tax_deductible": False,
            "tax_category": "Non-Deductible Personal Living",
            "cadence": "monthly",
            "action_insight": "UK TV Licence monthly payment scheme."
        },
        "welcome_brentford": {
            "name": "Welcome (Brentford)",
            "domain": "welcome-stores.co.uk",
            "merchant_type": "Independent Convenience Store",
            "category_l1": "Groceries & Essentials",
            "category_l2": "Convenience & Mini-Markets",
            "category_l3": "Local Grocery Store",
            "is_contractual_commitment": False,
            "is_essential_living_cost": True,
            "hmrc_tax_deductible": False,
            "tax_category": "Non-Deductible Personal Living",
            "cadence": "discretionary_one_off",
            "action_insight": "In-store POS contactless card payment at local Brentford convenience grocery store."
        },
        "sainsburys": {
            "name": "Sainsbury's",
            "domain": "sainsburys.co.uk",
            "merchant_type": "Supermarket Chain",
            "category_l1": "Groceries & Essentials",
            "category_l2": "Supermarkets",
            "category_l3": "National Supermarket Chain",
            "is_contractual_commitment": False,
            "is_essential_living_cost": True,
            "hmrc_tax_deductible": False,
            "tax_category": "Non-Deductible Personal Living",
            "cadence": "discretionary_one_off",
            "action_insight": "Supermarket groceries and essential household spend."
        },
        "tesco": {
            "name": "Tesco",
            "domain": "tesco.com",
            "merchant_type": "Supermarket Chain",
            "category_l1": "Groceries & Essentials",
            "category_l2": "Supermarkets",
            "category_l3": "National Supermarket Chain",
            "is_contractual_commitment": False,
            "is_essential_living_cost": True,
            "hmrc_tax_deductible": False,
            "tax_category": "Non-Deductible Personal Living",
            "cadence": "discretionary_one_off",
            "action_insight": "Routine supermarket food and household groceries."
        },
        "anthropic": {
            "name": "Anthropic PBC",
            "domain": "anthropic.com",
            "merchant_type": "Artificial Intelligence / SaaS",
            "category_l1": "Subscriptions & Software",
            "category_l2": "Developer Tools & AI",
            "category_l3": "AI Assistant & API Platform",
            "is_contractual_commitment": True,
            "is_essential_living_cost": False,
            "hmrc_tax_deductible": True,
            "tax_category": "Office & Software Costs",
            "cadence": "monthly",
            "action_insight": "Allowable professional expense under UK HMRC rules for software/AI tools."
        },
        "openai": {
            "name": "OpenAI",
            "domain": "openai.com",
            "merchant_type": "Artificial Intelligence / SaaS",
            "category_l1": "Subscriptions & Software",
            "category_l2": "Developer Tools & AI",
            "category_l3": "ChatGPT Plus / API Platform",
            "is_contractual_commitment": True,
            "is_essential_living_cost": False,
            "hmrc_tax_deductible": True,
            "tax_category": "Office & Software Costs",
            "cadence": "monthly",
            "action_insight": "Software subscription eligible for professional tax relief if used for business."
        },
        "github": {
            "name": "GitHub",
            "domain": "github.com",
            "merchant_type": "Developer Tools / SaaS",
            "category_l1": "Subscriptions & Software",
            "category_l2": "Developer Tools & AI",
            "category_l3": "Version Control & CI/CD",
            "is_contractual_commitment": True,
            "is_essential_living_cost": False,
            "hmrc_tax_deductible": True,
            "tax_category": "Office & Software Costs",
            "cadence": "monthly",
            "action_insight": "Developer software tooling. Allowable sole-trader / business expense."
        },
        "spotify": {
            "name": "Spotify",
            "domain": "spotify.com",
            "merchant_type": "Digital Audio Streaming",
            "category_l1": "Subscriptions & Software",
            "category_l2": "Digital Media & Entertainment",
            "category_l3": "Music Streaming Subscription",
            "is_contractual_commitment": True,
            "is_essential_living_cost": False,
            "hmrc_tax_deductible": False,
            "tax_category": "Non-Deductible Personal Living",
            "cadence": "monthly",
            "action_insight": "Discretionary digital entertainment subscription."
        },
        "netflix": {
            "name": "Netflix",
            "domain": "netflix.com",
            "merchant_type": "Digital Video Streaming",
            "category_l1": "Subscriptions & Software",
            "category_l2": "Digital Media & Entertainment",
            "category_l3": "Video-on-Demand Subscription",
            "is_contractual_commitment": True,
            "is_essential_living_cost": False,
            "hmrc_tax_deductible": False,
            "tax_category": "Non-Deductible Personal Living",
            "cadence": "monthly",
            "action_insight": "Discretionary digital video streaming subscription."
        },
        "tfl": {
            "name": "Transport for London",
            "domain": "tfl.gov.uk",
            "merchant_type": "Metropolitan Public Transit",
            "category_l1": "Transport & Commute",
            "category_l2": "Public Transit",
            "category_l3": "Underground, Bus & Rail Contactless",
            "is_contractual_commitment": False,
            "is_essential_living_cost": True,
            "hmrc_tax_deductible": True,
            "tax_category": "Travel & Subsistence",
            "cadence": "discretionary_one_off",
            "action_insight": "London public transport fare. Allowable travel expense if traveling for business meetings."
        },
        "dvla": {
            "name": "DVLA Swansea",
            "domain": "gov.uk/dvla",
            "merchant_type": "Government Executive Agency",
            "category_l1": "Transport & Commute",
            "category_l2": "Vehicle & Driver Licensing",
            "category_l3": "Driving Licence & Road Tax",
            "is_contractual_commitment": False,
            "is_essential_living_cost": True,
            "hmrc_tax_deductible": False,
            "tax_category": "Non-Deductible Personal Living",
            "cadence": "annual",
            "action_insight": "Official UK government driver or vehicle licensing charge."
        },
        "wise": {
            "name": "Wise Payments",
            "domain": "wise.com",
            "merchant_type": "Cross-Border FinTech",
            "category_l1": "Transfers & Remittance",
            "category_l2": "Foreign Exchange",
            "category_l3": "International Money Transfer",
            "is_contractual_commitment": False,
            "is_essential_living_cost": False,
            "hmrc_tax_deductible": False,
            "tax_category": "Non-Deductible Personal Living",
            "cadence": "discretionary_one_off",
            "action_insight": "International currency exchange or transfer. Neutral net worth impact if moving between own accounts."
        }
    }

    def clean_narrative(self, raw: str) -> Tuple[str, str]:
        """
        Cleans raw statement narratives by stripping POS aggregators, Faster Payments tags,
        BACS codes, terminal hashes, and bank statement noise.
        Returns: (canonical_slug, clean_display_name)
        """
        if not raw:
            return "unknown", "Unknown Merchant"

        text = raw.strip()

        # 1. Strip common POS terminal & aggregator prefixes
        pos_prefix_pattern = (
            r'^(SUMUP\s*\*|IZ\s*\*|SQ\s*\*|SQUARE\s*\*|STRIPE\s*\*|PAYPAL\s*\*|'
            r'CRV\s*\*|KLARNA\s*\*|AMZN\s+Mktp\s+UK\s*\*?|AMZ\s*\*?|SP\s*\*|'
            r'DIRECT\s+DEBIT\s+|DD\s+|SO\s+|FPO\s+|BGC\s+)'
        )
        text = re.sub(pos_prefix_pattern, '', text, flags=re.IGNORECASE).strip()

        # 2. Strip Faster Payments and statement noise suffixes (e.g. FP 01/10/26, TPP MONEYHUB..., VIA MOBILE)
        bank_noise_pattern = (
            r'\b(VIA\s+MOBILE|PYMT|FP\s+\d{2}/\d{2}/\d{2}|\bTPP\s+[A-Z0-9]+|'
            r'\bBGC\b|\bCHQ\b|\bREF\b|\bCD\s+\d{4}\b|\bCARD\s+\d{4}\b|\bMBP\b).*$'
        )
        text = re.sub(bank_noise_pattern, '', text, flags=re.IGNORECASE).strip()

        # 3. Strip long alphanumeric hash IDs / terminal codes (e.g. LTD7F56CFA33)
        text = re.sub(r'[A-F0-9]{8,}', '', text).strip()

        # 4. Clean punctuation and collapse spaces
        clean_name = re.sub(r'[\*\-_,]+', ' ', text)
        clean_name = re.sub(r'\s+', ' ', clean_name).strip()

        if not clean_name:
            clean_name = raw.strip()

        # 5. Create canonical slug for indexing
        canonical_key = re.sub(r'[^a-z0-9]+', '_', clean_name.lower()).strip('_')
        return canonical_key, clean_name

    def _resolve_knowledge_base_hit(self, canonical_key: str, clean_name: str, amount: float = 0.0) -> Optional[Dict[str, Any]]:
        """Matches canonical key against curated knowledge base with fuzzy keyword and amount fallbacks."""
        amt = abs(amount)

        # Contextual amount-aware disambiguation for Apple (Sub vs Hardware)
        if "apple" in canonical_key.lower():
            if amt <= 50.0:
                return {
                    "name": "Apple Services",
                    "domain": "apple.com",
                    "merchant_type": "Cloud Software & Digital Media",
                    "category_l1": "Subscriptions & Software",
                    "category_l2": "Cloud Storage & Media",
                    "category_l3": "iCloud+ & Digital Subscriptions",
                    "is_contractual_commitment": True,
                    "is_essential_living_cost": False,
                    "hmrc_tax_deductible": True,
                    "tax_category": "Office & Software Costs",
                    "cadence": "monthly",
                    "action_insight": "Apple digital services subscription (e.g. iCloud storage, developer plan, or Apple Music)."
                }
            else:
                return {
                    "name": "Apple Store",
                    "domain": "apple.com",
                    "merchant_type": "Consumer Electronics Retailer",
                    "category_l1": "Shopping & Lifestyle",
                    "category_l2": "Consumer Electronics",
                    "category_l3": "Hardware & Equipment",
                    "is_contractual_commitment": False,
                    "is_essential_living_cost": False,
                    "hmrc_tax_deductible": True,
                    "tax_category": "Office Equipment / Capital Assets",
                    "cadence": "discretionary_one_off",
                    "action_insight": "Hardware purchase at Apple Store. Eligible for capital allowance / equipment write-off if used for business."
                }

        # Direct exact match
        if canonical_key in self.PRESEEDED_KNOWLEDGE_BASE:
            return self.PRESEEDED_KNOWLEDGE_BASE[canonical_key]

        # Substring / keyword fuzzy match
        key_lower = canonical_key.lower()
        if "switch2" in key_lower:
            return self.PRESEEDED_KNOWLEDGE_BASE["switch2_energy"]
        if "thames_water" in key_lower or "thames" in key_lower:
            return self.PRESEEDED_KNOWLEDGE_BASE["thames_water"]
        if "british_gas" in key_lower:
            return self.PRESEEDED_KNOWLEDGE_BASE["british_gas"]
        if "hounslow" in key_lower or "council_tax" in key_lower:
            return self.PRESEEDED_KNOWLEDGE_BASE["lb_hounslow"]
        if "tv_licence" in key_lower or "tv_licensing" in key_lower:
            return self.PRESEEDED_KNOWLEDGE_BASE["tv_licence"]
        if "welcome" in key_lower and "brentford" in key_lower:
            return self.PRESEEDED_KNOWLEDGE_BASE["welcome_brentford"]
        if "sainsbury" in key_lower:
            return self.PRESEEDED_KNOWLEDGE_BASE["sainsburys"]
        if "tesco" in key_lower:
            return self.PRESEEDED_KNOWLEDGE_BASE["tesco"]
        if "anthropic" in key_lower or "claude" in key_lower:
            return self.PRESEEDED_KNOWLEDGE_BASE["anthropic"]
        if "openai" in key_lower or "chatgpt" in key_lower:
            return self.PRESEEDED_KNOWLEDGE_BASE["openai"]
        if "github" in key_lower:
            return self.PRESEEDED_KNOWLEDGE_BASE["github"]
        if "spotify" in key_lower:
            return self.PRESEEDED_KNOWLEDGE_BASE["spotify"]
        if "netflix" in key_lower:
            return self.PRESEEDED_KNOWLEDGE_BASE["netflix"]
        if "tfl" in key_lower or "transport_for_london" in key_lower:
            if amt > 40.0:
                return {
                    "name": "Transport for London",
                    "domain": "tfl.gov.uk",
                    "merchant_type": "Metropolitan Public Transit",
                    "category_l1": "Transport & Commute",
                    "category_l2": "Fines & Penalties",
                    "category_l3": "TfL Penalty Fare / Disputed Charge",
                    "is_contractual_commitment": False,
                    "is_essential_living_cost": False,
                    "hmrc_tax_deductible": False,
                    "tax_category": "Non-Deductible Fines & Penalties",
                    "cadence": "discretionary_one_off",
                    "action_insight": "⚠️ High TfL charge detected (>£40.00). May represent a penalty fare or card maximum fare charge."
                }
            return self.PRESEEDED_KNOWLEDGE_BASE["tfl"]
        if "dvla" in key_lower:
            return self.PRESEEDED_KNOWLEDGE_BASE["dvla"]
        if "wise" in key_lower:
            return self.PRESEEDED_KNOWLEDGE_BASE["wise"]

        return None

    def _infer_smart_model_or_fallback(self, tx: TransactionInput, clean_name: str, canonical_key: str) -> Dict[str, Any]:
        """
        Uses frontier smart model (Gemini 2.5 Flash via LLMClient) to enrich novel merchants,
        falling back to deterministic heuristics if in offline test environment.
        """
        amt = abs(tx.amount)
        # Check for Apple contextual disambiguation by amount
        if "apple" in canonical_key:
            if amt <= 25.0:
                return {
                    "name": "Apple Services",
                    "domain": "apple.com",
                    "merchant_type": "Cloud Software & Digital Media",
                    "category_l1": "Subscriptions & Software",
                    "category_l2": "Cloud Storage & Media",
                    "category_l3": "iCloud+ & Digital Subscriptions",
                    "is_contractual_commitment": True,
                    "is_essential_living_cost": False,
                    "hmrc_tax_deductible": True,
                    "tax_category": "Office & Software Costs",
                    "cadence": "monthly",
                    "action_insight": "Apple digital services subscription (e.g. iCloud storage or Apple Music)."
                }
            else:
                return {
                    "name": "Apple Retail",
                    "domain": "apple.com",
                    "merchant_type": "Consumer Electronics Retailer",
                    "category_l1": "Shopping & Lifestyle",
                    "category_l2": "Consumer Electronics",
                    "category_l3": "Hardware & Accessories",
                    "is_contractual_commitment": False,
                    "is_essential_living_cost": False,
                    "hmrc_tax_deductible": True,
                    "tax_category": "Office Equipment / Capital Assets",
                    "cadence": "discretionary_one_off",
                    "action_insight": "Hardware purchase at Apple Store. Potential capital allowance / equipment deduction for business."
                }

        # Try Smart Model invocation via LLMClient
        try:
            from fiduciary.agent.llm_client import LLMClient
            client = LLMClient()
            system_prompt = (
                "You are an expert UK Financial Transaction Enrichment & Entity Resolution Engine. "
                "Analyze the transaction counterparty narrative and return a strictly valid, compact JSON object "
                "with the following keys:\n"
                "- merchant_name: clean corporate merchant name\n"
                "- domain: primary official website domain (e.g. brand.co.uk or brand.com)\n"
                "- merchant_type: business activity\n"
                "- category_l1: top-level category\n"
                "- category_l2: sub-category\n"
                "- category_l3: fine-grained taxonomy\n"
                "- payment_channel: inferred payment rail (e.g. POS Contactless, Online Checkout, Direct Debit)\n"
                "- is_contractual: boolean true if recurring contract or utility\n"
                "- is_essential: boolean true if housing/utilities/groceries\n"
                "- hmrc_tax_deductible: boolean true if allowable UK sole-trader/business expense\n"
                "- tax_category: HMRC expense category\n"
                "- cadence: 'monthly' | 'weekly' | 'annual' | 'discretionary_one_off'\n"
                "- action_insight: concise 1-sentence fiduciary commentary."
            )
            prompt = (
                f"Raw Narrative: {tx.raw_narrative}\n"
                f"Clean Candidate: {clean_name}\n"
                f"Amount: {tx.amount} {tx.currency}\n"
                f"Payment Rail Hint: {tx.payment_rail or 'card'}\n\n"
                "Return ONLY raw JSON, with no markdown code blocks or backticks."
            )
            response = client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                caller="enrichment_engine",
                temperature=0.0
            )
            if response and not response.startswith("⚠️") and not response.startswith("❌"):
                clean_json = re.sub(r'^```json\s*', '', response.strip())
                clean_json = re.sub(r'```$', '', clean_json).strip()
                parsed = json.loads(clean_json)
                return {
                    "name": parsed.get("merchant_name") or clean_name.title(),
                    "domain": parsed.get("domain") or f"{canonical_key}.com",
                    "merchant_type": parsed.get("merchant_type", "Commercial Entity"),
                    "category_l1": parsed.get("category_l1", "General Spend"),
                    "category_l2": parsed.get("category_l2", "Uncategorized"),
                    "category_l3": parsed.get("category_l3", "General Transaction"),
                    "is_contractual_commitment": bool(parsed.get("is_contractual", False)),
                    "is_essential_living_cost": bool(parsed.get("is_essential", False)),
                    "hmrc_tax_deductible": bool(parsed.get("hmrc_tax_deductible", False)),
                    "tax_category": parsed.get("tax_category", "Non-Deductible Personal Living"),
                    "cadence": parsed.get("cadence", "discretionary_one_off"),
                    "action_insight": parsed.get("action_insight", f"Transaction with {clean_name.title()}.")
                }
        except Exception as e:
            logger.debug(f"LLM enrichment fallback activated for {clean_name}: {e}")

        # Deterministic semantic heuristic fallback
        return {
            "name": clean_name.title(),
            "domain": f"{canonical_key}.co.uk" if "uk" in canonical_key else f"{canonical_key}.com",
            "merchant_type": "Merchant / Service Provider",
            "category_l1": "General Spend",
            "category_l2": "Retail & Services",
            "category_l3": "General Commerce",
            "is_contractual_commitment": False,
            "is_essential_living_cost": False,
            "hmrc_tax_deductible": False,
            "tax_category": "Non-Deductible Personal Living",
            "cadence": "discretionary_one_off",
            "action_insight": f"Standard payment to {clean_name.title()}."
        }

    def enrich_single(self, tx: TransactionInput) -> EnrichedTransaction:
        """Enriches a single transaction through the 3-tier cascade."""
        canonical_key, clean_name = self.clean_narrative(tx.raw_narrative)
        source = "deterministic_rule"
        data = None

        # 1. Knowledge Base hit (Tier 1)
        kb_hit = self._resolve_knowledge_base_hit(canonical_key, clean_name, tx.amount)
        if kb_hit:
            data = kb_hit
            source = "deterministic_rule"

        # 2. SQLite Cache hit (Tier 1b)
        if not data:
            cached = get_cached_enrichment(canonical_key)
            if cached:
                data = {
                    "name": cached["merchant_name"],
                    "domain": cached.get("domain"),
                    "logo_url": cached.get("logo_url"),
                    "merchant_type": cached.get("merchant_type", "Commercial Entity"),
                    "category_l1": cached["category_l1"],
                    "category_l2": cached.get("category_l2"),
                    "category_l3": cached.get("category_l3"),
                    "is_contractual_commitment": bool(cached.get("is_contractual_commitment")),
                    "is_essential_living_cost": bool(cached.get("is_essential_living_cost")),
                    "hmrc_tax_deductible": bool(cached.get("hmrc_tax_deductible")),
                    "tax_category": cached.get("tax_category"),
                    "confidence_score": cached.get("confidence_score", 0.95),
                    "action_insight": cached.get("action_insight", "")
                }
                source = "cache_hit"

        # 3. Smart Model / Semantic Reasoning (Tier 2)
        if not data:
            data = self._infer_smart_model_or_fallback(tx, clean_name, canonical_key)
            source = "smart_model"
            # Persist to cache so future transactions are instant 0ms hits
            save_cached_enrichment(canonical_key, {
                "merchant_name": data["name"],
                "canonical_id": f"mch_{canonical_key}",
                "domain": data.get("domain"),
                "logo_url": f"https://img.logo.dev/{data.get('domain')}" if data.get("domain") else None,
                "merchant_type": data.get("merchant_type"),
                "category_l1": data["category_l1"],
                "category_l2": data.get("category_l2"),
                "category_l3": data.get("category_l3"),
                "is_contractual_commitment": data.get("is_contractual_commitment", False),
                "is_essential_living_cost": data.get("is_essential_living_cost", False),
                "hmrc_tax_deductible": data.get("hmrc_tax_deductible", False),
                "tax_category": data.get("tax_category"),
                "confidence_score": 0.98 if source == "smart_model" else 0.95,
                "action_insight": data.get("action_insight", "")
            })

        # Infer payment channel
        payment_channel = "POS In-Store Contactless"
        raw_upper = tx.raw_narrative.upper()
        if "DIRECT DEBIT" in raw_upper or "DD" in raw_upper:
            payment_channel = "Direct Debit Mandate"
        elif "STANDING ORDER" in raw_upper or "SO" in raw_upper:
            payment_channel = "Standing Order"
        elif "TPP" in raw_upper or "FP" in raw_upper:
            payment_channel = "Faster Payments TPP"
        elif any(k in raw_upper for k in [".COM", ".CO.UK", "ONLINE", "WWW", "HTTP"]):
            payment_channel = "Online Web Checkout"

        clean_merchant = CleanMerchant(
            name=data["name"],
            canonical_id=f"mch_{canonical_key}",
            domain=data.get("domain"),
            logo_url=f"https://img.logo.dev/{data.get('domain')}" if data.get("domain") else None,
            merchant_type=data.get("merchant_type", "Commercial Entity"),
            country="GB"
        )

        enrichment_details = EnrichmentDetails(
            category_l1=data["category_l1"],
            category_l2=data.get("category_l2") or data["category_l1"],
            category_l3=data.get("category_l3") or data.get("category_l2") or data["category_l1"],
            payment_channel=payment_channel,
            is_contractual_commitment=bool(data.get("is_contractual_commitment", False)),
            confidence_score=float(data.get("confidence_score", 0.98 if source == "deterministic_rule" else 0.92))
        )

        fiduciary_insights = FiduciaryInsights(
            cadence=data.get("cadence", "discretionary_one_off"),
            expected_amount_range=[round(abs(tx.amount) * 0.95, 2), round(abs(tx.amount) * 1.05, 2)] if data.get("is_contractual_commitment") else None,
            is_essential_living_cost=bool(data.get("is_essential_living_cost", False)),
            hmrc_tax_deductible=bool(data.get("hmrc_tax_deductible", False)),
            tax_category=data.get("tax_category"),
            action_insight=data.get("action_insight") or f"Transaction processed with {clean_merchant.name}."
        )

        return EnrichedTransaction(
            raw_narrative=tx.raw_narrative,
            amount=tx.amount,
            currency=tx.currency,
            booking_date=tx.booking_date,
            clean_merchant=clean_merchant,
            enrichment=enrichment_details,
            fiduciary_insights=fiduciary_insights,
            source=source
        )

    def enrich_batch(self, txs: List[TransactionInput]) -> BatchEnrichResponse:
        """Enriches a batch of transactions with latency profiling and cache metrics."""
        start_t = time.perf_counter()
        results: List[EnrichedTransaction] = []
        cache_hits = 0
        smart_model_hits = 0

        for tx in txs:
            res = self.enrich_single(tx)
            if res.source == "cache_hit":
                cache_hits += 1
            elif res.source == "smart_model":
                smart_model_hits += 1
            results.append(res)

        elapsed_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
        return BatchEnrichResponse(
            total_transactions=len(results),
            enriched_transactions=results,
            cache_hits=cache_hits,
            smart_model_hits=smart_model_hits,
            processing_time_ms=elapsed_ms
        )
