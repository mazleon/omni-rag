"""Initialize Qdrant collections for all existing organizations."""
import asyncio
import sys
sys.path.insert(0, ".")

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PayloadSchemaType, TextIndexParams, KeywordIndexParams, IntegerIndexParams
from qdrant_client.http.models.models import KeywordIndexType, IntegerIndexType

from core.config import settings
from core.db import engine, async_session_factory
from core.models import Org
from sqlalchemy import select


async def init_qdrant():
    client = QdrantClient(url=settings.QDRANT_URL)
    
    async with async_session_factory() as session:
        result = await session.execute(select(Org))
        orgs = result.scalars().all()
    
    org_slugs = [org.slug for org in orgs]
    if not org_slugs:
        org_slugs = ["default"]
    
    for org_slug in org_slugs:
        collection_name = f"chunks_{org_slug}"
        
        try:
            existing = client.get_collections().collections
            existing_names = [c.name for c in existing]
            
            if collection_name in existing_names:
                print(f"Collection {collection_name} already exists, skipping")
                continue
            
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
            )
            print(f"Created collection: {collection_name}")
            
            # Create payload indices for filtered search
            client.create_payload_index(
                collection_name=collection_name,
                field_name="document_id",
                field_schema=KeywordIndexParams(type=KeywordIndexType.KEYWORD),
            )
            client.create_payload_index(
                collection_name=collection_name,
                field_name="modality",
                field_schema=KeywordIndexParams(type=KeywordIndexType.KEYWORD),
            )
            client.create_payload_index(
                collection_name=collection_name,
                field_name="doc_type",
                field_schema=KeywordIndexParams(type=KeywordIndexType.KEYWORD),
            )
            client.create_payload_index(
                collection_name=collection_name,
                field_name="created_at_epoch",
                field_schema=IntegerIndexParams(type=IntegerIndexType.INTEGER),
            )
            print(f"  Created payload indices for {collection_name}")
            
        except Exception as e:
            print(f"Error creating collection {collection_name}: {e}")
    
    print(f"\nQdrant initialized with {len(org_slugs)} collection(s)")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_qdrant())
