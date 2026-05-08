from p2dmd import escape


def escape_md(text: str) -> str:
    try:
        return escape(text)
    except Exception:
        return text
