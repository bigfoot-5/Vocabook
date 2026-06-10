import os
import time
from pinecone import Pinecone, ServerlessSpec
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

class SimpleDocument:
    """Helper class to match LangChain document interface"""
    def __init__(self, page_content, metadata):
        self.page_content = page_content
        self.metadata = metadata

class PineconeManager:
    def __init__(self, index_name="vocab-book"):
        self.index_name = index_name
        
        self.pinecone_api_key = os.getenv("PINECONE_API")
        if not self.pinecone_api_key:
            self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
            
        if not self.pinecone_api_key:
            raise ValueError("PINECONE_API not found in .env")
            
        self.google_api_key = os.getenv("GEMINI_API_KEY")
        if not self.google_api_key:
             raise ValueError("GEMINI_API_KEY not found in .env")

        self.pc = Pinecone(api_key=self.pinecone_api_key)
        
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=self.google_api_key
        )
        
        self._ensure_index()

    def _ensure_index(self):
        """Check if index exists, create if not."""
        existing_indexes = [i.name for i in self.pc.list_indexes()]
        
        if self.index_name not in existing_indexes:
            print(f"Creating Pinecone index: {self.index_name}")
            self.pc.create_index(
                name=self.index_name,
                dimension=768,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )

            while not self.pc.describe_index(self.index_name).status['ready']:
                time.sleep(1)
            print("Index created and ready.")
        else:
            print(f"Using existing Pinecone index: {self.index_name}")

    def index_texts(self, texts, metadatas=None):
        """Direct index via Pinecone Client."""
        index = self.pc.Index(self.index_name)
        
        try:
            pass
        except Exception as e:
            print(f"Warning clearing index: {e}")

        print(f"Generating embeddings for {len(texts)} chunks...")
        embeddings = self.embeddings.embed_documents(texts)
        
        vectors_to_upsert = []
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            meta = metadatas[i] if metadatas else {}
            meta['text'] = text
            vector_id = f"{meta.get('spine_index', 0)}_{meta.get('p_index', i)}"
            
            vectors_to_upsert.append({
                "id": vector_id,
                "values": embedding,
                "metadata": meta
            })
            
        print(f"Upserting {len(vectors_to_upsert)} vectors to Pinecone...")
        batch_size = 100
        for i in range(0, len(vectors_to_upsert), batch_size):
            index.upsert(vectors=vectors_to_upsert[i:i+batch_size])
            
        print("Indexing complete.")

    def similarity_search(self, query, k=3):
        """Find relevant text chunks."""
        index = self.pc.Index(self.index_name)
        
        query_embedding = self.embeddings.embed_query(query)
        
        results = index.query(
            vector=query_embedding,
            top_k=k,
            include_metadata=True
        )
        
        docs = []
        for match in results.matches:
            text = match.metadata.get('text', '')
            docs.append(SimpleDocument(page_content=text, metadata=match.metadata))
            
        return docs
