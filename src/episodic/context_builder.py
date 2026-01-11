# context_builder.py
from .hybrid_retriever import HybridRetriever
from .redis_stm import search_stm, store_stm


def build_context(user_id, user_input, deepdive_id=None):
    # 1️⃣ STM semantic cache
    stm = search_stm(user_id, user_input)
    if stm:
        return stm

    # 2️⃣ Episodic memory
    retriever = HybridRetriever()
    retriever.load(user_id, deepdive_id)
    results = retriever.search(user_input)

    context = []
    for r in results:
        ep = r["episode"]
        text = "\n".join(
            f"{m['role']}: {m['content']}"
            for m in ep["messages"]
        )
        context.append({
            "role": "system",
            "content": f"PAST EPISODE:\n{text}"
        })

    if context:
        store_stm(user_id, user_input, context)

    return context
