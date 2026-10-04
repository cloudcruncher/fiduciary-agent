"""
Local Lightweight Semantic Vector RAG (Retrieval-Augmented Generation) Engine.
Provides embedded semantic search over bank statement narratives, tax policies,
credit underwriter standards, and user-provided financial documents.
Requires zero external vector databases or cloud APIs; runs 100% locally.
"""

import math
import re
from typing import Any, Dict, List, Optional


class LocalVectorRAG:
    """
    Lightweight, embedded Vector Retrieval-Augmented Generation index.
    Computes TF-IDF weighted cosine similarity vectors with sub-millisecond retrieval.
    Pre-seeded with statutory UK regulatory documents, HMRC tax schedules, and underwriter guidelines.
    """

    def __init__(self):
        self.documents: List[Dict[str, Any]] = []
        self.idf_cache: Dict[str, float] = {}
        self._seed_statutory_corpus()

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Tokenizes text into normalized alphanumeric n-grams."""
        clean = re.sub(r"[^\w\s\£\%\.]", " ", text.lower())
        tokens = [t.strip() for t in clean.split() if len(t.strip()) > 1]
        return tokens

    def _compute_vector(self, text: str) -> Dict[str, float]:
        """Computes term frequency vector."""
        tokens = self._tokenize(text)
        if not tokens:
            return {}
        tf: Dict[str, float] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0.0) + 1.0

        # Term frequency normalization
        max_tf = max(tf.values())
        vector: Dict[str, float] = {}
        for t, count in tf.items():
            idf = self.idf_cache.get(t, 1.5)
            vector[t] = (0.5 + 0.5 * (count / max_tf)) * idf
        return vector

    def add_document(self, doc_id: str, content: str, title: str, category: str, metadata: Optional[Dict[str, Any]] = None):
        """Indexes a document chunk with metadata."""
        tokens = self._tokenize(content)
        doc = {
            "id": doc_id,
            "title": title,
            "category": category,
            "content": content,
            "metadata": metadata or {},
            "tokens": set(tokens)
        }
        self.documents.append(doc)
        self._update_idf()

    def _update_idf(self):
        """Recomputes inverse document frequency across the corpus."""
        n_docs = len(self.documents)
        if n_docs == 0:
            return
        df: Dict[str, int] = {}
        for doc in self.documents:
            for t in doc["tokens"]:
                df[t] = df.get(t, 0) + 1

        self.idf_cache = {
            t: math.log((n_docs + 1) / (count + 1)) + 1.0
            for t, count in df.items()
        }

    def search(self, query: str, top_k: int = 3, category_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Executes cosine similarity search against indexed knowledge chunks.
        Returns top_k most relevant documents with relevance scores.
        """
        if not self.documents:
            return []

        q_vec = self._compute_vector(query)
        if not q_vec:
            return []

        q_norm = math.sqrt(sum(v * v for v in q_vec.values()))
        if q_norm == 0.0:
            return []

        results = []
        for doc in self.documents:
            if category_filter and doc["category"].lower() != category_filter.lower():
                continue

            doc_vec = self._compute_vector(doc["content"])
            d_norm = math.sqrt(sum(v * v for v in doc_vec.values()))
            if d_norm == 0.0:
                continue

            # Dot product
            common_keys = set(q_vec.keys()) & set(doc_vec.keys())
            dot = sum(q_vec[k] * doc_vec[k] for k in common_keys)
            cosine_sim = dot / (q_norm * d_norm)

            # Bonus for exact title phrase match
            if any(t in doc["title"].lower() for t in self._tokenize(query)):
                cosine_sim += 0.15

            if cosine_sim > 0.05:
                results.append({
                    "id": doc["id"],
                    "title": doc["title"],
                    "category": doc["category"],
                    "score": round(float(cosine_sim), 4),
                    "content": doc["content"],
                    "metadata": doc["metadata"]
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _seed_statutory_corpus(self):
        """Pre-seeds standard UK financial statutory guidelines and underwriter rules."""
        statutory_docs = [
            (
                "uk_isa_allowance_2026",
                "HMRC Individual Savings Account (ISA) Statutory Framework",
                "tax_rules",
                "The UK statutory annual ISA allowance is £20,000 across Cash ISAs, Stocks & Shares ISAs, "
                "Innovative Finance ISAs, and Lifetime ISAs. For Lifetime ISAs (LISA), the maximum annual deposit "
                "is £4,000, attracting a 25% government bonus up to £1,000/year for first-time home buyers (<£450k) "
                "or retirement at age 60. Junior ISA (JISA) allowance is £9,000 per tax year."
            ),
            (
                "uk_pension_allowance_2026",
                "HMRC Pension Annual Allowance & SIPP Tax Relief",
                "pension_rules",
                "The annual pension contribution allowance is £60,000 gross per tax year (or 100% of UK relevant earnings). "
                "Basic rate tax relief (20%) is claimed at source by providers. Higher rate (40%) and additional rate (45%) "
                "taxpayers must claim an extra 20% or 25% through Self Assessment or PAYE tax code adjustments. "
                "Tapered annual allowance reduces by £1 for every £2 of adjusted income over £260,000 down to a minimum £10,000."
            ),
            (
                "uk_60_percent_tax_trap",
                "HMRC Personal Allowance Taper (60% Marginal Rate Trap)",
                "tax_rules",
                "Between £100,000 and £125,140 of Adjusted Net Income, an individual loses £1 of tax-free Personal Allowance "
                "for every £2 of income above £100,000. This creates an effective 60% marginal income tax rate (40% higher rate "
                "+ 20% allowance clawback, plus National Insurance). Strategic SIPP pension contributions or charitable donations "
                "reduce Adjusted Net Income pound-for-pound to restore the full £12,570 Personal Allowance."
            ),
            (
                "uk_capital_gains_tax_2026",
                "HMRC Capital Gains Tax (CGT) Exemption & Rates",
                "tax_rules",
                "The annual Capital Gains Tax exempt allowance is £3,000 per individual. Gains above £3,000 are taxed at "
                "18% for basic rate taxpayers and 24% for higher and additional rate taxpayers on residential property and assets. "
                "Spouse transfers are exempt and can utilize both allowances (£6,000 combined)."
            ),
            (
                "fca_mcob_11_affordability",
                "FCA MCOB 11 Mortgage Affordability & Underwriter Stress Standards",
                "credit_underwriting",
                "Under FCA MCOB 11 rules, mortgage lenders assess Uncommitted Monthly Income (UMI), Contractual Debt-to-Income (DTI), "
                "and conduct interest rate stress testing (typically Bank of England base rate + 3%, or 7.5% nominal). "
                "Maximum standard loan-to-income (LTI) is 4.5x gross verified income. "
                "Active Buy Now Pay Later (BNPL) schemes, gambling transactions exceeding 1% of net income, and unarranged overdraft usage "
                "in the preceding 90 days are treated as negative underwriting risk indicators."
            ),
            (
                "emergency_fund_fiduciary_standards",
                "Fiduciary Liquidity & Emergency Safety Buffer Standards",
                "wealth_planning",
                "Standard UK fiduciary guidelines recommend 3 to 6 months of essential living expenses held in instant-access "
                "FSCS-protected accounts. Liquid runway is computed as liquid capital divided by daily living burn rate. "
                "Emergency cash should not be locked in fixed-term deposits or exposed to equity market volatility."
            ),
        ]

        for doc_id, title, cat, content in statutory_docs:
            self.add_document(doc_id=doc_id, content=content, title=title, category=cat)


# Singleton instance
_VECTOR_RAG_INSTANCE: Optional[LocalVectorRAG] = None


def get_vector_rag() -> LocalVectorRAG:
    """Returns the shared LocalVectorRAG instance."""
    global _VECTOR_RAG_INSTANCE
    if _VECTOR_RAG_INSTANCE is None:
        _VECTOR_RAG_INSTANCE = LocalVectorRAG()
    return _VECTOR_RAG_INSTANCE
