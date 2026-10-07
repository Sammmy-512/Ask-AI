import re


def chunk_text(text: str, max_size: int = 1000) -> list[str]:
    chunks = []
    current_chunk = ""

    # Normalize Windows line endings
    text = text.replace("\r\n", "\n")

    # Split into paragraphs first
    paragraphs = text.split("\n\n")

    for paragraph in paragraphs:
        paragraph = paragraph.strip()

        if not paragraph:
            continue

        # Large paragraph -> split into sentences
        if len(paragraph) > max_size:
            sentences = re.split(r'(?<=[.!?])\s+', paragraph)

            for sentence in sentences:
                sentence = sentence.strip()

                if not sentence:
                    continue

                # Extremely large sentence -> hard split
                if len(sentence) > max_size:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                        current_chunk = ""

                    for beginning in range(0, len(sentence), max_size):
                        piece = sentence[beginning:beginning + max_size].strip()

                        if piece:
                            chunks.append(piece)

                    continue

                # Add sentence if it fits
                if len(current_chunk) + len(sentence) + 1 <= max_size:
                    current_chunk += sentence + " "

                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())

                    current_chunk = sentence + " "

        # Normal paragraph
        else:
            if len(current_chunk) + len(paragraph) + 2 <= max_size:
                current_chunk += paragraph + "\n\n"

            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())

                current_chunk = paragraph + "\n\n"

    # Save final remaining chunk
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks