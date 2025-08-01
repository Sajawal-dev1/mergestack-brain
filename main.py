# main.py

# import sys
# from src.clickup.ingest_all import ingest_all_clickup_data
# from src.clickup.utils import get_all_namespaces
# from src.rag.rag_pipeline import run_rag_pipeline


# def main():
#         ingest_all_clickup_data()

# if __name__ == "__main__":
#     main()

# main.py

from src.rag.rag_pipeline import run_rag_pipeline
from src.clickup.utils import get_all_namespaces

def main():
    namespaces = get_all_namespaces()

    if not namespaces:
        print("❌ No namespaces found. Have you ingested any data yet?")
        return

    print("\n📂 Available Namespaces:")
    for i, ns in enumerate(namespaces):
        print(f"{i + 1}. {ns['team_name']} > {ns['space_name']} ({ns['namespace']})")

    try:
        choice = int(input("\n🔍 Select a namespace by number: ")) - 1
        selected_namespace = namespaces[choice]["namespace"]
    except (IndexError, ValueError):
        print("❌ Invalid selection.")
        return

    while True:
        question = input("\n💬 Ask a question (or type 'exit'): ")
        if question.lower() == "exit":
            break

        try:
            answer = run_rag_pipeline(question, namespace=selected_namespace)
            print(f"\n🤖 Answer:\n{answer}")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()

