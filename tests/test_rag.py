from aetherforge.rag.hybrid import HybridIndex
from aetherforge.rag.seed_docs import DOCUMENTS, chunk_documents


def test_hybrid_finds_hvac_runbook():
    chunks = chunk_documents(DOCUMENTS)
    index = HybridIndex(chunks)
    hits = index.search("HVAC zone temperature drift damper sensor", k=3)
    assert hits
    assert any("HVAC" in h.doc_id or "HVAC" in h.title for h in hits)


def test_hybrid_finds_postgres_playbook():
    chunks = chunk_documents()
    hits = HybridIndex(chunks).search("postgresql replica lag failover", k=3)
    assert any(h.doc_id == "SOP-PG-011" for h in hits)


def test_chunking_covers_all_docs():
    chunks = chunk_documents()
    doc_ids = {c["doc_id"] for c in chunks}
    assert doc_ids == {d["doc_id"] for d in DOCUMENTS}
