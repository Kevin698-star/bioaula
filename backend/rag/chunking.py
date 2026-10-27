def split_text(text, chunk_size=500, overlap=100):
    if not text or not text.strip():
        return []

    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    chunks = []
    current = ''

    for para in paragraphs:
        if not para:
            continue

        if len(para) > chunk_size:
            if current:
                chunks.append(current)
                current = ''
            words = para.split()
            temp = ''
            for w in words:
                candidate = (temp + ' ' + w).strip() if temp else w
                if len(candidate) > chunk_size:
                    if temp:
                        chunks.append(temp)
                    temp = w
                else:
                    temp = candidate
            if temp:
                current = temp
            continue

        candidate = (current + '\n\n' + para).strip() if current else para
        if len(candidate) > chunk_size:
            chunks.append(current)
            if overlap > 0 and chunks:
                prev = chunks[-1]
                overlap_text = prev[-overlap:] if len(prev) > overlap else prev
                current = overlap_text + '\n\n' + para
            else:
                current = para
        else:
            current = candidate

    if current:
        chunks.append(current)

    return [c for c in chunks if c.strip()]
