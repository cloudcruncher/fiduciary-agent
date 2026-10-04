from fiduciary.agent.vector_rag import LocalVectorRAG, get_vector_rag


def test_vector_rag_statutory_corpus():
    rag = get_vector_rag()
    results = rag.search("what is the isa allowance limit", top_k=2)

    assert len(results) > 0
    top = results[0]
    assert "ISA" in top["title"] or "ISA" in top["content"]
    assert top["score"] > 0.1
    assert "20,000" in top["content"]


def test_vector_rag_60_percent_tax_trap():
    rag = get_vector_rag()
    results = rag.search("60 percent marginal tax rate trap personal allowance", top_k=2)

    assert len(results) > 0
    match_ids = [r["id"] for r in results]
    assert "uk_60_percent_tax_trap" in match_ids or "uk_pension_allowance_2026" in match_ids


def test_vector_rag_custom_document():
    rag = LocalVectorRAG()
    rag.add_document(
        doc_id="home_insurance_policy_2026",
        title="Aviva Home Insurance Policy",
        category="insurance",
        content="Policy number AV-987654 covers building sum insured £450,000 and contents £75,000 with excess £250.",
        metadata={"provider": "Aviva", "excess_gbp": 250}
    )

    res = rag.search("what is my home insurance excess", top_k=1)
    assert len(res) == 1
    assert res[0]["id"] == "home_insurance_policy_2026"
    assert "excess £250" in res[0]["content"]
