import uuid
from chat_service import add_super_chat_message
from context_builder import build_context
from llm import call_llm

USER_ID = "11111111-1111-1111-1111-111111111111"


def run_cli():
    print("🧠 Context-Aware Chat (CLI)")
    print("Type 'exit' to quit\n")

    while True:
        user_input = input("You: ")
        if user_input.lower() in ("exit", "quit"):
            print("👋 Goodbye")
            break

        # Store user message
        add_super_chat_message(USER_ID, "user", user_input)

        # Build context using hybrid retrieval
        context = build_context(USER_ID, user_input)

        if context:
            print(f"────────── 🔎 RETRIEVED CONTEXT ({len(context)} episodes) ──────────")
            for i, ctx in enumerate(context):
                meta = ctx.get('metadata', {})
                ep = meta.get('episode', {})
                print(f"[EPISODE {i+1}]")
                print(f"Source      : {ep.get('source_type', 'unknown')}")
                print(f"Episode ID  : {ep.get('id', 'N/A')}")
                date_from = ep.get('date_from', 'N/A')
                date_to = ep.get('date_to', 'N/A')
                print(f"Date Range  : {date_from} → {date_to}")
                print(f"Vector Score: {meta.get('vector_score', 0):.4f}")
                print(f"BM25 Score  : {meta.get('bm25_score', 0):.4f}")
                print()
                print("PAST CONTEXT:")
                messages = ep.get('messages', [])
                for msg in messages:
                    print(f"{msg['role']}: {msg['content']}")
                print()
            print("──────────────────────────────────────────────────────")
        else:
            print("🔍 No relevant context retrieved.")

        context_for_llm = [{"role": ctx["role"], "content": ctx["content"]} for ctx in context]

        context_for_llm.append({
            "role": "user",
            "content": user_input
        })

        # Call LLM
        response = call_llm(context_for_llm)

        # Store assistant response
        add_super_chat_message(USER_ID, "assistant", response)

        print("\nAssistant:", response, "\n")

if __name__ == "__main__":
    run_cli()
