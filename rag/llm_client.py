import anthropic

from config import ANTHROPIC_API_KEY, MODEL_NAME, SYSTEM_PROMPT
from rag.retriever import assemble_user_message


def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def ask_claude(question: str, context_block: str) -> dict:
    """
    Send a RAG-augmented question to Claude.

    Returns:
        {"answer": str, "input_tokens": int, "output_tokens": int}
    """
    client = get_client()
    user_message = assemble_user_message(question, context_block)

    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=2048,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    answer = response.content[0].text
    return {
        "answer": answer,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
