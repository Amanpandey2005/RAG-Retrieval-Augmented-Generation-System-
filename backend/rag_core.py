import os
import time
import uuid
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Third-party integrations
from pinecone import Pinecone, ServerlessSpec
import cohere
import google.generativeai as genai
from openai import OpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

class RAGEngine:
    def __init__(self):
        # Configuration
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_index_name = os.getenv("PINECONE_INDEX_NAME", "mini-rag-index")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.cohere_api_key = os.getenv("COHERE_API_KEY")
        
        # Initialize Clients
        if self.pinecone_api_key:
            self.pc = Pinecone(api_key=self.pinecone_api_key)
        else:
            self.pc = None
            print("Warning: PINECONE_API_KEY not found.")

        if self.cohere_api_key:
            self.co = cohere.Client(self.cohere_api_key)
        else:
            self.co = None
            print("Warning: COHERE_API_KEY not found.")

        # Determine Embedding & LLM Provider (Prefer OpenAI, fallback to Gemini)
        self.provider = "openai" if self.openai_api_key else "gemini"
        
        if self.provider == "openai":
            self.openai_client = OpenAI(api_key=self.openai_api_key)
            self.embedding_model = "text-embedding-3-small"
            self.embedding_dim = 1536
        else:
            if self.gemini_api_key:
                genai.configure(api_key=self.gemini_api_key)
                self.embedding_model = "models/text-embedding-004"
                self.embedding_dim = 768
            else:
                print("Warning: No LLM/Embedding provider keys found.")

    def ensure_index(self):
        """Creates the Pinecone index if it doesn't exist."""
        if not self.pc: raise ValueError("Pinecone client not initialized.")
        
        existing_indexes = [i.name for i in self.pc.list_indexes()]
        if self.pinecone_index_name not in existing_indexes:
            # Create index
            self.pc.create_index(
                name=self.pinecone_index_name,
                dimension=self.embedding_dim,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1") # defaulting to common region
            )
            # Wait for eventual consistency
            while not self.pc.describe_index(self.pinecone_index_name).status['ready']:
                time.sleep(1)

        self.index = self.pc.Index(self.pinecone_index_name)

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a list of texts."""
        if self.provider == "openai":
            response = self.openai_client.embeddings.create(
                input=texts,
                model=self.embedding_model
            )
            return [data.embedding for data in response.data]
        else:
            # Gemini
            results = []
            for text in texts:
                result = genai.embed_content(
                    model=self.embedding_model,
                    content=text,
                    task_type="retrieval_document"
                )
                results.append(result['embedding'])
            return results

    def get_query_embedding(self, text: str) -> List[float]:
        """Generates embedding for a single query."""
        if self.provider == "openai":
            response = self.openai_client.embeddings.create(
                input=text,
                model=self.embedding_model
            )
            return response.data[0].embedding
        else:
            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="retrieval_query"
            )
            return result['embedding']

    def chunk_text(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 150) -> List[str]:
        """Chunks text using RecursiveCharacterTextSplitter."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        return splitter.split_text(text)

    def ingest_document(self, text: str, metadata: Dict[str, Any]):
        """Chunks, embeds, and upserts text to Pinecone."""
        self.ensure_index()
        
        chunks = self.chunk_text(text)
        embeddings = self.get_embeddings(chunks)
        
        vectors = []
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            vector_id = f"{metadata.get('doc_id')}_{i}"
            # Add chunk specific metadata
            chunk_metadata = metadata.copy()
            chunk_metadata['text'] = chunk
            chunk_metadata['chunk_index'] = i
            
            vectors.append({
                "id": vector_id,
                "values": emb,
                "metadata": chunk_metadata
            })
            
        # Batch upsert (Pinecone limit is usually 100-200 vectors per request)
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i+batch_size]
            self.index.upsert(vectors=batch)
            
        return len(vectors)

    def search(self, query: str, top_k: int = 20) -> List[Dict]:
        """Retrieves and then reranks results."""
        self.ensure_index()
        
        # 1. Retrieval
        query_emb = self.get_query_embedding(query)
        results = self.index.query(
            vector=query_emb,
            top_k=top_k,
            include_metadata=True
        )
        
        matches = results['matches']
        docs = [match['metadata']['text'] for match in matches]
        
        if not docs:
            return []

        # 2. Rerank (if Cohere is available)
        if self.co:
            rerank_results = self.co.rerank(
                model='rerank-english-v3.0',
                query=query,
                documents=docs,
                top_n=5 # Return top 5 after reranking
            )
            
            final_results = []
            for rr in rerank_results.results:
                # Map back to original metadata
                original_match = matches[rr.index]
                final_results.append({
                    "score": rr.relevance_score,
                    "text": original_match['metadata']['text'],
                    "metadata": original_match['metadata']
                })
            return final_results
        
        else:
            # Fallback if no reranker: just return top 5 by vector score
            final_results = []
            for match in matches[:5]:
                final_results.append({
                    "score": match['score'],
                    "text": match['metadata']['text'],
                    "metadata": match['metadata']
                })
            return final_results

    def generate_answer(self, query: str, context_chunks: List[Dict]) -> Dict:
        """Generates answer using LLM."""
        
        # Prepare context with visible citation markers
        context_text = ""
        for i, chunk in enumerate(context_chunks):
            # [1], [2], etc.
            context_text += f"Source [{i+1}]: {chunk['text']}\n\n"
            
        system_prompt = (
            "You are an intelligent assistant designed to provide abstractive answers. "
            "Synthesize the information from the provided context to answer the user's question in a cohesive and fluent manner. "
            "Do not simply extract or copy-paste text. "
            "Base your answer ONLY on the provided context sources. "
            "If the answer is not in the context, say 'I cannot answer this based on the provided documents'. "
            "Cite your sources using square brackets like [1] or [2] at the end of sentences where appropriate."
        )
        
        user_prompt = f"Context:\n{context_text}\n\nQuestion: {query}"
        
        if self.provider == "openai":
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini", # Cost effective
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            answer = response.choices[0].message.content
        else:
            # Gemini
            # Using gemini-2.5-flash as requested
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(system_prompt + "\n" + user_prompt)
            answer = response.text
            
        return {
            "answer": answer,
            "citations": context_chunks
        }
