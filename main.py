import os
import warnings
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub

from src.calibre_db import CalibreDB
from src.epub_utils import EpubManager
from src.cfi_generator import calculate_cfi, get_element_cfi

# Suppress warnings
warnings.filterwarnings('ignore')

# Configuration
LIBRARY_PATH = '/Users/karthiktalluri/Calibre Library'
BOOK_ID = 22
TARGET_TEXT = "initialization"

def main():
    print(f"Initializing Calibre DB at {LIBRARY_PATH}")
    db = CalibreDB(LIBRARY_PATH)
    
    book_dir = db.get_book_path(BOOK_ID)
    if not book_dir:
        print(f"Book data for ID {BOOK_ID} not found in database.")
        return
        
    print(f"Located book directory: {book_dir}")
    
    epub_path = EpubManager.find_epub_file(book_dir)
    if not epub_path:
        print("EPUB file not found in book directory.")
        return
        
    print(f"Reading EPUB: {epub_path}")
    book = EpubManager.read_book(epub_path)
    if not book:
        return

    # Detect OPF root directory manually to fix spine_name mismatch
    import zipfile
    import xml.etree.ElementTree as ET
    from src.vector_db import PineconeManager
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.prompts import PromptTemplate
    
    opf_root_dir = ""
    try:
        with zipfile.ZipFile(epub_path, 'r') as z:
            # Find the rootfile path from META-INF/container.xml
            container_xml = z.read('META-INF/container.xml')
            root = ET.fromstring(container_xml)
            ns = {'ns': 'urn:oasis:names:tc:opendocument:xmlns:container'}
            rootfile_path = root.find('.//ns:rootfile', ns).attrib['full-path']
            if '/' in rootfile_path:
                opf_root_dir = rootfile_path.rsplit('/', 1)[0]
    except Exception as e:
        print(f"Warning: Could not detect OPF root: {e}")

    # --- BACKUP ---
    import shutil
    backup_path = epub_path + ".bak"
    try:
        print(f"Creating backup at: {backup_path}")
        shutil.copy2(epub_path, backup_path)
    except Exception as e:
        print(f"Failed to create backup: {e}")
        return
    try:
        # 1. Get "Start Here" location
        print("Checking for 'Start Here' annotation...")
        start_spine_index, start_cfi_raw = db.get_start_annotation(BOOK_ID, "Start Here")
        
        start_cfi_tuple = None
        if start_spine_index is not None and start_cfi_raw:
            print(f"Found 'Start Here' at Chapter Index {start_spine_index}, CFI: {start_cfi_raw}")
            # Parse CFI string to tuple for comparison (e.g. "/2/4/6:0" -> (2, 4, 6))
            # 1. Remove offset part
            path_only = start_cfi_raw.split(':')[0]
            # 2. Split by slash, filter empty
            parts = [int(x) for x in path_only.split('/') if x.isdigit()]
            start_cfi_tuple = tuple(parts)
        else:
            print("No 'Start Here' note found. Processing from beginning.")
            start_spine_index = -1 

        pages_to_process = 5 # Default limit or prompt user
        print(f"Processing first {pages_to_process} HTML items (subject to filter)...")
        
        # Collect text chunks
        chunks = []
        metadatas = []
        
        # We need a way to map chunks back to spine items for rewriting
        # Structure: list of (index, item_id, soup)
        processable_items = []
        
        count = 0
        for i, (item_id, linear) in enumerate(book.spine):
            # 1. Global skip for previous chapters
            if i < start_spine_index:
                continue
                
            if count >= pages_to_process: break
            
            item = book.get_item_with_id(item_id)
            if not item or not isinstance(item, ebooklib.epub.EpubHtml): continue
            
            soup = BeautifulSoup(item.content, 'html.parser')
            text = soup.get_text()
            if len(text) < 50: continue # Skip empty/nav pages
            
            # Simple chunking by paragraphs for this demo
            paragraphs = [p for p in soup.find_all('p') if p.get_text().strip()]
            
            skipped_count = 0
            for p_idx, p in enumerate(paragraphs):
                 # Filter check: "Start Here" logic
                 if i == start_spine_index and start_cfi_tuple:
                     p_path = get_element_cfi(p)
                     if p_path:
                         p_parts = [int(x) for x in p_path.split('/') if x.isdigit()]
                         p_tuple = tuple(p_parts)
                         if p_tuple < start_cfi_tuple:
                             skipped_count += 1
                             continue

                 # Store metadata to find specific paragraph later
                 chunks.append(p.get_text())
                 metadatas.append({"spine_index": i, "p_index": p_idx, "file_name": item.file_name})
            
            if skipped_count > 0:
                print(f"  Chapter {i}: Skipped {skipped_count} paragraphs before 'Start Here'.")
            
            processable_items.append((i, item, soup))
            count += 1
            
        if not chunks:
            print("No text found to process.")
            return

        # Vector Search
        print("Initializing Pinecone and embedding text...")
        pc_manager = PineconeManager()
        pc_manager.index_texts(chunks, metadatas)
        
        print(f"Searching for context relevant to: '{TARGET_TEXT}'")
        results = pc_manager.similarity_search(TARGET_TEXT, k=5)
        
        # LLM Setup
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=os.getenv("GEMINI_API_KEY"))
        rewrite_prompt = PromptTemplate.from_template(
            "Rewrite the following text, replacing any synonyms of '{target}' with the word '{target}'. "
            "Keep the rest of the text exactly the same. Output ONLY the rewritten text.\n\nText: {text}"
        )
        
        modified = False
        
        # Process results
        # To avoid rewriting same paragraph multiple times if it matches multiple queries, we can track IDs
        # But here we just process the top k unique paragraphs
        processed_indices = set()
        
        for res in results:
            meta = res.metadata
            unique_id = f"{meta['spine_index']}_{meta['p_index']}"
            if unique_id in processed_indices: continue
            
            original_text = res.page_content
            # Check if target is already there? user wants to replace SYNONYMS
            
            print(f"Rewriting matching paragraph in {meta['file_name']}...")
            import time
            time.sleep(4) # Rate limit handling
            chain = rewrite_prompt | llm
            rewritten_text = chain.invoke({"target": TARGET_TEXT, "text": original_text}).content.strip()
            
            # Find the paragraph in the book object to update
            # We need to re-find the item and soup. 
            # Optimization: We have processable_items, but we need correct scope.
            # Let's map spine_index to the item/soup from our list
            target_item_data = next((x for x in processable_items if x[0] == int(meta['spine_index'])), None)
            
            if target_item_data:
                _, item, soup = target_item_data
                # Find specific paragraph by index (simple approximation)
                paragraphs = [p for p in soup.find_all('p') if p.get_text().strip()]
                if int(meta['p_index']) < len(paragraphs):
                    p_tag = paragraphs[int(meta['p_index'])]
                    p_tag.string = rewritten_text
                    item.content = str(soup).encode('utf-8')
                    modified = True
                    processed_indices.add(unique_id)
                    
                    # Add highlight immediately for the NEW text
                    # We need to re-calculate CFI on the modified soup
                    # Note: We are highlighting the TARGET_TEXT in the modified paragraph
                    path_str, _, offsets = calculate_cfi(soup, TARGET_TEXT)
                    if path_str:
                         spine_cfi = (int(meta['spine_index']) + 1) * 2
                         full_start_cfi = f"/{spine_cfi}{path_str}:{offsets[0]}"
                         full_end_cfi = f"/{spine_cfi}{path_str}:{offsets[1]}"
                         
                         final_spine_name = item.file_name
                         if opf_root_dir and not item.file_name.startswith(opf_root_dir):
                            final_spine_name = f"{opf_root_dir}/{item.file_name}"
                            
                         db.add_annotation(
                            BOOK_ID, 
                            TARGET_TEXT, 
                            full_start_cfi.replace(f"/{spine_cfi}", ""), 
                            full_end_cfi.replace(f"/{spine_cfi}", ""),
                            spine_cfi, 
                            final_spine_name
                        )
                         print(f"Added highlight for rewritten term in {final_spine_name}")

        if modified:
            # Debug: Check for None content
            for it in book.get_items():
                if it.content is None:
                    print(f"DEBUG WARNING: Item {it.id} ({it.get_type()}) has None content!")
                    
            print("Saving modified EPUB...")
            epub.write_epub(epub_path, book)
            
            # Post-write verification
            print("Verifying written file...")
            if os.path.getsize(epub_path) < 1000:
                raise Exception("Written file is too small (possible corruption).")
            
            try:
                with zipfile.ZipFile(epub_path, 'r') as z:
                    if z.testzip() is not None:
                        raise Exception("Written file has bad zip structure.")
            except Exception as zip_err:
                 raise Exception(f"Written file could not be opened: {zip_err}")
                 
            print("Verification passed! Book updated.")
        else:
            print("No changes made.")
            
    except Exception as e:
        print(f"\nCRITICAL ERROR in rewrite workflow: {e}")
        import traceback
        traceback.print_exc()
        
        print(f"\nRestoring backup from {backup_path}...")
        try:
            shutil.copy2(backup_path, epub_path)
            print("Restoration successful.")
        except Exception as restore_error:
            print(f"FAILED TO RESTORE BACKUP: {restore_error}")

    # Old logic kept for reference or single search fallback?
    # For now, we override the loop to prioritize the workflow above.
    return
    
    if found:
        print("Done! Annotation added. Please restart Calibre to view.")
    else:
        print(f"Text '{TARGET_TEXT}' not found in the book.")

if __name__ == "__main__":
    main()
