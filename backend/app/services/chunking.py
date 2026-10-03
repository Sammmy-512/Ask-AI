def chunk_text(text: str) -> list[str]:
    chunks = []
    beginning = 0

    for i in range(len(text)):
        if text[i] == '\n\n':
            chunk = text[beginning:i]
            chunks.append(chunk)
            beginning = i + 1

    if beginning < len(text):
        chunks.append(text[beginning:])

    return chunks