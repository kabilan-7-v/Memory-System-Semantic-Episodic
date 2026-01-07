from hybrid_retriever import HybridRetriever

def build_context(user_id, user_input, deepdive_id=None):
    retriever = HybridRetriever()
    retriever.load(user_id, deepdive_id)

    results = retriever.search(user_input)

    context = []
    for result in results:
        ep = result['episode']
        context.append({
            "role": "system",
            "content": f"PAST EPISODE:\n{ep['messages']}",
            "metadata": result  # include scores etc
        })

    return context