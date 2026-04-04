def get_parser_service():
    from services.ingestion.parser import get_parser_service as _get
    return _get()

def get_chunker_service():
    from services.ingestion.chunker import get_chunker_service as _get
    return _get()

def get_embedder_service():
    from services.ingestion.embedder import get_embedder_service as _get
    return _get()

__all__ = ["get_parser_service", "get_chunker_service", "get_embedder_service"]
