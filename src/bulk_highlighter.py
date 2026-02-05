import nltk
from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet
from nltk.tokenize import TreebankWordTokenizer
import sqlite3
import warnings
from bs4 import BeautifulSoup
import ebooklib
# epub_utils manager and cfi_gen
from src.calibre_db import CalibreDB
from src.epub_utils import EpubManager
from src.cfi_generator import get_element_cfi

warnings.filterwarnings('ignore')

# Check and download NLTK resources
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab')
    
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')
    
try:
    nltk.data.find('taggers/averaged_perceptron_tagger')
except LookupError:
    nltk.download('averaged_perceptron_tagger')
try:
    nltk.data.find('taggers/averaged_perceptron_tagger_eng')
except LookupError:
    nltk.download('averaged_perceptron_tagger_eng')

# Configuration
LIBRARY_PATH = '/Users/karthiktalluri/Calibre Library'
BOOK_ID = 24
DB_PATH = 'vocabook.db'
LIMIT_PAGES = 5

def get_wordnet_pos(treebank_tag):
    if treebank_tag.startswith('J'):
        return wordnet.ADJ
    elif treebank_tag.startswith('V'):
        return wordnet.VERB
    elif treebank_tag.startswith('N'):
        return wordnet.NOUN
    elif treebank_tag.startswith('R'):
        return wordnet.ADV
    else:
        return wordnet.NOUN

def load_gre_words():
    print(f"Loading words from {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT word, definition FROM words")
    rows = cursor.fetchall()
    conn.close()
    
    word_dict = {}
    lemmatizer = WordNetLemmatizer()
    tokenizer = TreebankWordTokenizer()
    
    # Pre-process dictionary keys to be lower case
    count = 0
    for w, d in rows:
        if not w: continue
        word_dict[w.lower()] = d
        count += 1
        
    print(f"Loaded {count} words.")
    return word_dict

def process_book(book_id, start_cfi=None, end_cfi=None):
    print(f"Starting bulk highlighter for Book ID {book_id}")
    if start_cfi:
        print(f"Start Point: {start_cfi}")
    if end_cfi:
        print(f"End Point: {end_cfi}")

    gre_words = load_gre_words()
    
    lemmatizer = WordNetLemmatizer()
    
    db = CalibreDB(LIBRARY_PATH)
    book_dir = db.get_book_path(book_id)
    if not book_dir:
        print("Book not found.")
        return

    epub_path = EpubManager.find_epub_file(book_dir)
    print(f"Reading EPUB: {epub_path}")
    book = EpubManager.read_book(epub_path)
    if not book: return

    # Detect OPF root directory
    import zipfile
    import xml.etree.ElementTree as ET
    
    opf_root_dir = ""
    try:
        with zipfile.ZipFile(epub_path, 'r') as z:
            container_xml = z.read('META-INF/container.xml')
            root = ET.fromstring(container_xml)
            ns = {'ns': 'urn:oasis:names:tc:opendocument:xmlns:container'}
            rootfile_path = root.find('.//ns:rootfile', ns).attrib['full-path']
            if '/' in rootfile_path:
                opf_root_dir = rootfile_path.rsplit('/', 1)[0]
    except Exception as e:
        print(f"Warning: Could not detect OPF root: {e}")

    processed_count = 0
    matches_found = 0
    
    print("Fetching existing highlights to avoid duplicates...")
    existing_highlights = db.get_existing_highlights(book_id)
    print(f"Found {len(existing_highlights)} existing highlights.")
    
    # helper to parse CFI for simple comparison
    def parse_cfi_tuple(cfi_str):
        # /spine_idx/node_path:offset
        # e.g. /2/4/10:0
        if not cfi_str: return None
        try:
            body = cfi_str.replace("epubcfi(", "").replace(")", "")
            # Split path and offset
            path, offset = body.split(':') if ':' in body else (body, "0")
            parts = [int(x) for x in path.split('/') if x.isdigit()]
            return tuple(parts), int(offset)
        except:
            return None

    start_tuple, start_offset = (None, 0)
    if start_cfi:
        res = parse_cfi_tuple(start_cfi)
        if res: start_tuple, start_offset = res
        
    end_tuple, end_offset = (None, 0)
    if end_cfi:
        res = parse_cfi_tuple(end_cfi)
        if res: end_tuple, end_offset = res

    # 0-based spine index vs CFI spine index?
    # CFI usually uses (spine_index + 1) * 2. 
    # e.g. spine 0 -> /2
    # So if start_tuple is (2, ...), that matches spine_index 0.
    
    for i, (item_id, linear) in enumerate(book.spine):
        # CFI spine value for this chapter
        current_spine_cfi_val = (i + 1) * 2
        
        # 1. Check Range (Chapter Level)
        # If we have a start_tuple like (4, ...), and current spine is 2. Skip.
        if start_tuple and current_spine_cfi_val < start_tuple[0]:
            print(f"Skipping Chapter {i} (Pre-Start)")
            continue
            
        # If we have an end_tuple like (6, ...), and current spine is 8. Stop.
        if end_tuple and current_spine_cfi_val > end_tuple[0]:
            print(f"Reached End Bookmark (Chapter {i}). Stopping.")
            break
            
        item = book.get_item_with_id(item_id)
        if not item or not isinstance(item, ebooklib.epub.EpubHtml): 
            continue
            
        # Fix spine name
        spine_name_normalized = item.file_name
        if opf_root_dir and not spine_name_normalized.startswith(opf_root_dir):
            spine_name_normalized = f"{opf_root_dir}/{spine_name_normalized}"
            
        soup = BeautifulSoup(item.content, 'html.parser')
        body = soup.body if soup.body else soup
        
        print(f"Processing Chapter {i} ({spine_name_normalized})...")
        
        # Iterate text nodes
        for text_node in body.find_all(text=True):
            text_content = str(text_node)
            if not text_content.strip(): continue
            
            # --- Check CFI Range (Node Level) ---
            # Should we process this node?
            # We assume we process UNLESS it falls outside strict bounds in start/end chapters.
            
            if (start_tuple and current_spine_cfi_val == start_tuple[0]) or \
               (end_tuple and current_spine_cfi_val == end_tuple[0]):
               
               # We are in a boundary chapter. Need node CFI.
               node_cfi_str = get_element_cfi(text_node)
               if not node_cfi_str: continue # safer to skip if can't loc
               
               # Current Node tuple: (element_path_tuple)
               # e.g. /4/2/6 -> (4, 2, 6). 
               # But get_element_cfi returns relative path inside body? 
               # get_element_cfi implementation likely returns path from body?
               # Let's verify standard: usually returns full path if passed full Doc?
               # Or relative?
               # Assuming get_element_cfi returns relative to 'html' or 'body'?
               # We need to construct full tuple comparable to start_tuple.
               # start_tuple includes main spine /2/. 
               # So we combine: (current_spine_cfi_val, ...node_parts)
               
                # Let's parse the returned relative path
               p_parts = [int(x) for x in node_cfi_str.split('/') if x.isdigit()]
               full_node_tuple = (current_spine_cfi_val, *p_parts)
               
               # Start Check
               if start_tuple and current_spine_cfi_val == start_tuple[0]:
                   # Compare tuples
                   # strict inequality: if full_node_tuple < start_tuple (lexicographic)
                   # Warning: start_tuple might have more depth (offset). 
                   # We just compare paths for node inclusion.
                   # If node is strictly before start node?
                   if full_node_tuple < start_tuple[:len(full_node_tuple)]:
                       continue
                   # Note: If same node, we ideally check offset. ignoring offset for bulk granularity.
               
               # End Check
               if end_tuple and current_spine_cfi_val == end_tuple[0]:
                   if full_node_tuple > end_tuple[:len(full_node_tuple)]:
                       continue

            # --- Highlighting Logic ---
            try:
                spans = list(TreebankWordTokenizer().span_tokenize(text_content))
            except LookupError:
                continue
            if not spans: continue
            
            tokens = [text_content[s:e] for s, e in spans]
            pos_tags = nltk.pos_tag(tokens)
            
            for idx, (token, tag) in enumerate(pos_tags):
                candidate = token.lower()
                definition = None
                
                if candidate in gre_words:
                    definition = gre_words[candidate]
                else:
                    wn_pos = get_wordnet_pos(tag)
                    lemma = lemmatizer.lemmatize(candidate, pos=wn_pos)
                    if lemma in gre_words:
                        definition = gre_words[lemma]
                    else:
                        for prefix in ['un', 'in', 'im', 'dis', 'non', 'Re']:
                            if candidate.startswith(prefix.lower()):
                                root = candidate[len(prefix):]
                                if root in gre_words:
                                    definition = gre_words[root]
                                    break
                                root_lemma = lemmatizer.lemmatize(root, pos=wn_pos)
                                if root_lemma in gre_words:
                                    definition = gre_words[root_lemma]
                                    break

                if definition:
                    start, end = spans[idx]
                    
                    node_cfi = get_element_cfi(text_node)
                    if not node_cfi: continue
                    
                    final_cfi_start = f"{node_cfi}:{start}"
                    final_cfi_end = f"{node_cfi}:{end}"
                    
                    # Full Absolute CFI for DB (including spine)
                    # DB expects valid Calibre CFI?
                    # DB uses relative CFI? 
                    # Existing code: final_cfi_start was just node_cfi + offset.
                    # Wait, line 184: final_cfi_start = f"{node_cfi}:{start}"
                    # And line 203: passed to db.add_annotation.
                    # db.add_annotation takes spine_index separately.
                    
                    if final_cfi_start in existing_highlights:
                        continue
                    
                    existing_highlights.add(final_cfi_start)
                    
                    print(f"Highlighting '{token}'")
                    
                    db.add_annotation(
                        book_id=book_id,
                        text=token,
                        cfi_start=final_cfi_start,
                        cfi_end=final_cfi_end,
                        spine_index=current_spine_cfi_val, 
                        spine_name=spine_name_normalized,
                        notes=f"<b>{candidate}</b>: {definition}",
                        color="blue"
                    )
                    matches_found += 1
                    
        processed_count += 1
    
    print(f"Finished. Added {matches_found} highlights.")
    
    # --- FSRS Sync ---
    try:
        from src.fsrs_manager import FSRSManager
        from dateutil import parser
        
        print("\n--- Syncing FSRS Reviews ---")
        fsrs = FSRSManager()
        
        # Re-fetch all highlights (including new ones) to sync status
        highlights = db.get_highlights_with_metadata(book_id)
        
        synced_count = 0
        for hl in highlights:
            color = hl['color']
            # Only process Blue (Good) or Yellow (Again)
            # Colors might be "blue", "yellow" or hex codes depending on setup.
            # Usually strict names in Calibre builtin styles.
            
            rating = 0
            if color == "blue":
                rating = 3 # Good
            elif color == "yellow":
                rating = 1 # Again
            
            if rating > 0:
                text = hl['text']
                ts_str = hl['timestamp']
                try:
                    # Parse timestamp (ISO 8601 with tz)
                    review_time = parser.parse(ts_str)
                    
                    # Clean text (remove punctuation?)
                    # Ideally words table stores lemmas or raw tokens? 
                    # Highlights might be phrases. 
                    # For now, assume single words or "candidate" token.
                    # We try to strict match the 'word' field in DB.
                    # If highlight is "checked", but DB has "check", we might miss it unless we lemmatize.
                    # fsrs_manager.process_review does strict lookup.
                    # We can try lemmatizing again here.
                    
                    # Simple approach: try raw, then lemmatized
                    candidates = [text.lower()]
                    
                    # Add Lemma
                    tokens = nltk.word_tokenize(text)
                    if len(tokens) == 1:
                        tag = nltk.pos_tag(tokens)[0][1]
                        lemma = lemmatizer.lemmatize(tokens[0].lower(), get_wordnet_pos(tag))
                        if lemma != candidates[0]:
                            candidates.append(lemma)
                    
                    for cand in candidates:
                         # We blindly call process_review. 
                         # It handles lookup and skips if not found.
                         # It also skips if review_time is old.
                         fsrs.process_review(cand, rating, review_time)
                         
                    synced_count += 1
                except Exception as e:
                    print(f"Error syncing highlight '{text}': {e}")
                    
        print(f"Synced {synced_count} highlights to FSRS.")
        
    except ImportError:
       print("FSRS module not found. Skipping sync.")
    except Exception as e:
       print(f"FSRS Sync Error: {e}")

if __name__ == "__main__":
    # Default test run
    process_book(BOOK_ID)
