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
from src.cfi_utils import is_element_in_range, parse_cfi_to_path
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
    # Fetch definition AND state
    cursor.execute("SELECT word, definition, state FROM words")
    rows = cursor.fetchall()
    conn.close()
    
    word_dict = {}
    
    # Pre-process dictionary keys to be lower case
    count = 0
    for w, d, s in rows:
        if not w: continue
        # Store definition and state. Handle None state as 0 (New)
        word_dict[w.lower()] = {
            'def': d,
            'state': s if s is not None else 0
        }
        count += 1
        
    print(f"Loaded {count} words.")
    return word_dict

def process_book(book_id, start_spine=0, end_spine=float('inf'), whitelist=None, start_cfi=None, end_cfi=None):
    print(f"Starting bulk highlighter for Book ID {book_id}")
    print(f"Range: Spine {start_spine} to {end_spine}")
    if start_cfi: print(f"Start CFI: {start_cfi}")
    if end_cfi: print(f"End CFI: {end_cfi}")

    gre_words = load_gre_words()
    
    # Whitelist Filtering
    if whitelist:
        whitelist_set = set(w.lower() for w in whitelist)
        gre_words = {k: v for k, v in gre_words.items() if k in whitelist_set}
        print(f"Whitelist active. Filtered to {len(gre_words)} words.")
        print(f"[DEBUG] Whitelisted Keys: {list(gre_words.keys())}")
    
    lemmatizer = WordNetLemmatizer()
    
    db = CalibreDB(LIBRARY_PATH)
    # ... (rest of loading code same) ... 
    book_dir = db.get_book_path(book_id)
    if not book_dir: return
    epub_path = EpubManager.find_epub_file(book_dir)
    book = EpubManager.read_book(epub_path)
    if not book: return
    
    # ... (OPF detection same) ...
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
    existing_highlights = db.get_existing_highlights(book_id)
    
    # Iterate Spine
    for i, (item_id, linear) in enumerate(book.spine):
        # 0-based spine index 'i'
        current_spine_cfi_val = (i + 1) * 2
        
        # Range Check
        if i < start_spine: continue
        if i > end_spine: break
            
        item = book.get_item_with_id(item_id)
        if not item or not isinstance(item, ebooklib.epub.EpubHtml): continue
            
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
            
            # --- Check CFI Granularity ---
            # If we are in the Start or End Spine chapter, we MUST check node CFI.
            # (If inside purely middle chapters, we can skip node usage check for speed, 
            # but usually start=end spine so we always check).
            
            check_needed = False
            if i == start_spine or i == end_spine:
                 check_needed = True
            
            if check_needed and (start_cfi or end_cfi):
                # Generate CFI for this node
                # Note: get_element_cfi usually returns relative path from body?
                # We need to construct full CFI to match the inputs?
                # Actually, our helper `is_element_in_range` expects full CFIs OR we pass canonicals.
                # `start_cfi` from DB is full `epubcfi(...)`.
                # We need to construct full CFI for this node.
                
                rel_cfi = get_element_cfi(text_node)
                if not rel_cfi: continue
                
                # Construct Full CFI: /spine_val/rel_cfi
                # rel_cfi usually is /4/2/1...
                # current_spine_cfi_val is 14 -> /14
                
                # WARNING: get_element_cfi implementation?
                # If it returns /4/2, and spine is /14. Combined: /14/4/2.
                
                # Let's ensure slash handling.
                if rel_cfi.startswith('/'):
                    node_full_cfi = f"/{current_spine_cfi_val}{rel_cfi}"
                else:
                    node_full_cfi = f"/{current_spine_cfi_val}/{rel_cfi}"
                    
                if not is_element_in_range(node_full_cfi, start_cfi, end_cfi):
                    # Skip this node
                    continue

            # DEBUG: Check if we see the target word
            if whitelist and any(w.lower() in text_content.lower() for w in whitelist):
                 print(f"[DEBUG] Processing eligible node. Found likely match.")

            # --- Highlighting Logic ---
            try:
                spans = list(TreebankWordTokenizer().span_tokenize(text_content))
            except LookupError:
                continue
            if not spans: continue
            
            tokens = [text_content[s:e] for s, e in spans]
            
            # DEBUG: If we suspected this node has the word, what are the tokens?
            if whitelist and any(w.lower() in text_content.lower() for w in whitelist):
                print(f"[DEBUG] Tokens in suspicious node: {tokens}")
            
            pos_tags = nltk.pos_tag(tokens)
            
            
            for idx, (token, tag) in enumerate(pos_tags):
                # Clean candidate (remove markdown *, _, punctuation)
                candidate = token.lower().strip('*_.,!?()[]{}"\'')
                if not candidate: continue
                
                definition = None
                state = 0
                
                # Check candidate
                if whitelist and candidate in gre_words:
                    print(f"[DEBUG] Direct Match: {candidate}")
                    
                if candidate in gre_words:
                    entry = gre_words[candidate]
                    definition = entry['def']
                    state = entry['state']
                else:
                    wn_pos = get_wordnet_pos(tag)
                    lemma = lemmatizer.lemmatize(candidate, pos=wn_pos)
                    if lemma in gre_words:
                        entry = gre_words[lemma]
                        definition = entry['def']
                        state = entry['state']
                    else:
                        for prefix in ['un', 'in', 'im', 'dis', 'non', 'Re']:
                            if candidate.startswith(prefix.lower()):
                                root = candidate[len(prefix):]
                                if root in gre_words:
                                    entry = gre_words[root]
                                    definition = entry['def']
                                    state = entry['state']
                                    break
                                root_lemma = lemmatizer.lemmatize(root, pos=wn_pos)
                                if root_lemma in gre_words:
                                    entry = gre_words[root_lemma]
                                    definition = entry['def']
                                    state = entry['state']
                                    break

                if definition:
                    start, end = spans[idx]
                    
                    node_cfi = get_element_cfi(text_node)
                    if not node_cfi: continue
                    
                    final_cfi_start = f"{node_cfi}:{start}"
                    final_cfi_end = f"{node_cfi}:{end}"
                    
                    if final_cfi_start in existing_highlights:
                        continue
                    
                    existing_highlights.add(final_cfi_start)
                    
                    # Determine Color based on State
                    color_map = {
                        0: "blue",   # New
                        1: "red",    # Learning / Again
                        2: "green",  # Review / Good
                        3: "orange"  # Relearning / Hard
                    }
                    nav_color = color_map.get(state, "blue")
                    
                    print(f"Highlighting '{token}' ({nav_color})")
                    
                    db.add_annotation(
                        book_id=book_id,
                        text=token,
                        cfi_start=final_cfi_start,
                        cfi_end=final_cfi_end,
                        spine_index=current_spine_cfi_val, 
                        spine_name=spine_name_normalized,
                        notes=f"{candidate}: {definition}",
                        color=nav_color
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
