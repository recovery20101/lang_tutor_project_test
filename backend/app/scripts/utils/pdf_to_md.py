import pymupdf4llm

# Конвертируем конкретные страницы (например, 13-15 про Nouns)
md_text = pymupdf4llm.to_markdown("Spanish essential grammar.pdf", pages=list(range(321, 334)))

# Сохраняем в файл для вашей базы знаний
with open("latin_vs_peninsular _base.md", "w", encoding="utf-8") as f:
    f.write(md_text)