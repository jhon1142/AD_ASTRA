from core.document import Document

doc = Document(
    doc_id="DOC001",
    fuente="ejemplo.pdf",
    formato="pdf",
    fenomeno=1,
    content="Texto extraído del documento de prueba.",
)

print(doc)
