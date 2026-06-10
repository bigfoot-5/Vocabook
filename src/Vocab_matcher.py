import os
from typing import TypedDict, List
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END

class SimpleTextSplitter:
    def __init__(self, chunk_size=1000, chunk_overlap=200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> List[str]:
        if not text:
            return []
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = start + self.chunk_size
            if end >= text_len:
                chunks.append(text[start:])
                break
            
            found_break = False
            for sep in ["\n\n", "\n", ". ", " "]:
                split_idx = text.rfind(sep, start, end)
                if split_idx != -1 and split_idx > start + (self.chunk_size // 2): 
                    end = split_idx + len(sep)
                    found_break = True
                    break
            
            chunks.append(text[start:end])
            start = end - self.chunk_overlap
            
            if start >= end:
                 start = end
        
        return chunks

load_dotenv()

class BatchGraphState(TypedDict):
    remaining_words: List[str]      # Words from CSV yet to be injected
    original_chunks: List[str]      # The input text split into chunks
    current_chunk_index: int        # Index of the chunk currently being processed
    processed_chunks: List[str]     # Resulting text chunks (rewritten or original)
    used_words: List[str]           # Track which words were successfully injected


class VocabBatchProcessor:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file")
            
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", 
            google_api_key=api_key,
            temperature=0
        )

    def process_chunk(self, state: BatchGraphState):
        """
        Analyzes the current chunk to see if any remaining words can be injected.
        If yes, rewrites the chunk.
        """
        print(f"[DEBUG] Inside process_chunk_with_gemini. State keys: {list(state.keys())}")
        current_index = state["current_chunk_index"]
        original_chunks = state["original_chunks"]
        words_to_check = state.get("remaining_words", []) # Default to empty list if not present
        
        if current_index >= len(original_chunks):
            print("[DEBUG] current_index is out of bounds. Returning empty results.")
            return {"processed_chunks": [], "used_words": []}

        chunk_text = original_chunks[current_index]
        
        idx = state['current_chunk_index']
        
        print(f"\n--- Processing Chunk {idx + 1}/{len(state['original_chunks'])} ---")
        print(f"Remaining Words: {len(words_to_check)}")

        if not words_to_check:
            return {
                "processed_chunks": state['processed_chunks'] + [chunk_text],
                "current_chunk_index": idx + 1
            }

        identify_prompt = ChatPromptTemplate.from_template(
            """
            You are a vocabulary expert.
            
            Text Chunk:
            "{chunk_text}"
            
            Target Words List:
            {words_list}
            
            Task:
            Identify which of the Target Words can be NATURALLY substituted into the text chunk 
            to replace simpler synonyms.
            
            Constraint:
            - Select ONLY words that have a direct or strong contextual synonym in the text.
            - Do not force a word if it doesn't fit.
            
            Output strictly a valid JSON list of the words found:
            ["word1", "word2"]
            If none fit, output: []
            """
        )
        
        identify_chain = identify_prompt | self.llm | StrOutputParser()
        
        matches = []
        try:
            result = identify_chain.invoke({
                "chunk_text": chunk_text,
                "words_list": ", ".join(words_to_check)
            })
            import json
            clean_json = result.replace("```json", "").replace("```", "").strip()
            matches = json.loads(clean_json)
        except Exception as e:
            print(f"Error identifying matches: {e}")
            matches = []
            
        valid_matches = [w for w in matches if w in words_to_check]
        
        missed = [w for w in words_to_check if w not in valid_matches]
        if missed:
            print(f"Words NOT matched in this chunk: {missed}")
        
        if not valid_matches:
            print(f"No suitable matches found for: {words_to_check}")
            return {
                "processed_chunks": state['processed_chunks'] + [chunk_text],
                "current_chunk_index": idx + 1
            }

        print(f"Found insertion opportunities for: {valid_matches}")
        
        rewrite_prompt = ChatPromptTemplate.from_template(
            """
            You are a skilled editor.
            
            Original Text:
            "{original_text}"
            
            Words to Inject: {words_to_inject}
            
            Task:
            Rewrite the text to incorporate the "Words to Inject".
            - Replace existing synonyms in the text with these target words.
            - Maintain the original meaning and flow.
            - Ensure grammatical correctness.
            - CRITICAL: Do NOT use markdown formatting (like **bold** or *italics*) for the injected words. Output clean text only.
            
            Return ONLY the rewritten text.
            """
        )
        
        rewrite_chain = rewrite_prompt | self.llm | StrOutputParser()
        
        rewritten_text = rewrite_chain.invoke({
            "original_text": chunk_text,
            "words_to_inject": ", ".join(valid_matches)
        })
        
        new_remaining = [w for w in words_to_check if w not in valid_matches]
        new_used = state.get('used_words', []) + valid_matches
        
        return {
            "processed_chunks": state['processed_chunks'] + [rewritten_text],
            "remaining_words": new_remaining,
            "current_chunk_index": idx + 1,
            "used_words": new_used
        }

    def build_graph(self):
        workflow = StateGraph(BatchGraphState)
        
        workflow.add_node("process_chunk", self.process_chunk)
        
        workflow.set_entry_point("process_chunk")
        
        def should_continue(state):
            if state['current_chunk_index'] >= len(state['original_chunks']):
                return END
            return "process_chunk"

        workflow.add_conditional_edges(
            "process_chunk",
            should_continue
        )
        
        return workflow.compile()

import sqlite3

def calculate_target_word_count(text: str, ratio: float) -> int:
    if not text: return 0
    token_count = len(text.split())
    count = int(token_count * ratio)
    return max(1, count) if token_count > 0 else 0

def process_batch_vocab(db_path, text_path, output_path, num_words=10, token_ratio=None):
    processor = VocabBatchProcessor()
    app = processor.build_graph()
    
    try:
        with open(text_path, 'r') as f:
            full_text = f.read()
            
        text_splitter = SimpleTextSplitter(
            chunk_size=1000,
            chunk_overlap=200, 
        )
        chunks = text_splitter.split_text(full_text)
        print(f"Split text into {len(chunks)} chunks.")
        
        if token_ratio is not None:
            token_count = len(full_text.split())
            calculated_num = int(token_count * token_ratio)
            num_words = max(1, calculated_num) if token_count > 0 else 0
            print(f"Token Count: {token_count}. Ratio: {token_ratio}. Calculated Target Words: {num_words}")
            
    except Exception as e:
        print(f"Error reading text: {e}")
        return

    try:
        if not os.path.exists(db_path):
             print(f"Error: Database not found at {db_path}")
             return
             
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        
        query = f"SELECT word FROM words ORDER BY (state = 0) ASC, due ASC LIMIT {num_words};"
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        target_words = [row[0] for row in rows if row[0]]
        target_words = [str(w).strip() for w in target_words if str(w).strip()]
        
        if not target_words:
            print("No words found in database.")
            return
            
        print(f"Loaded {len(target_words)} words from DB: {target_words}")
        
    except Exception as e:
        print(f"Error loading from DB: {e}")
        return

    inputs = {
        "remaining_words": target_words,
        "original_chunks": chunks,
        "current_chunk_index": 0,
        "processed_chunks": [],
        "used_words": []
    }
    
    print("Starting Batch Processing...")
    try:
        result = app.invoke(inputs)
        
        final_text = "\n\n".join(result['processed_chunks'])
        
        print("\n=== FINAL OUTPUT PREVIEW ===")
        print(final_text[:500])
        print(f"\nSuccessfully Injected: {result['used_words']}")
        print(f"Remaining (Not Injected): {result['remaining_words']}")
        
        with open(output_path, 'w') as f:
            f.write(final_text)
        print(f"Saved to {output_path}")
        
    except Exception as e:
        print(f"Error running graph: {e}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_file = os.path.join(base_dir, "vocabook.db")
    text_file = os.path.join(base_dir, "paragraph.txt")
    output_file = os.path.join(base_dir, "paragraph_rewritten.txt")
    
    token_ratio = 0.02 
    process_batch_vocab(db_file, text_file, output_file, token_ratio=token_ratio)
