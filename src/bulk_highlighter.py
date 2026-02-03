import nltk
from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet
from nltk.tokenize import TreebankWordTokenizer
import sqlite3
import warnings
from bs4 import BeautifulSoup
import ebooklib
# epub_utils manager and cfi_gen
from calibre_db import CalibreDB
from epub_utils import EpubManager
from cfi_generator import get_element_cfi

warnings.filterwarnings('ignore')

# Configuration
LIBRARY_PATH = '/Users/karthiktalluri/Calibre Library'
BOOK_ID = 23
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

def process_book():
    gre_words = load_gre_words()
    
    lemmatizer = WordNetLemmatizer()
    # Use standard word_tokenize for lemma generation logic
    # But use span_tokenize for offsets
    
    db = CalibreDB(LIBRARY_PATH)
    book_dir = db.get_book_path(BOOK_ID)
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

    print(f"Processing first {LIMIT_PAGES} spine items...")
    
    processed_count = 0
    matches_found = 0
    
    print("Fetching existing highlights to avoid duplicates...")
    existing_highlights = db.get_existing_highlights(BOOK_ID)
    print(f"Found {len(existing_highlights)} existing highlights.")
    
    # Pre-compute keys for fast lookup
    gre_keys = set(gre_words.keys())
    
    for i, (item_id, linear) in enumerate(book.spine):
        if processed_count >= LIMIT_PAGES:
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
        
        # Iterate text nodes
        for text_node in body.find_all(text=True):
            text_content = str(text_node)
            if not text_content.strip(): continue
            
            # Simple word extraction first to check overlap?
            # Or token scan.
            
            # Use span_tokenize to get word offsets
            # Then lemmatize each word
            
            # Warning: TreebankWordTokenizer splits "don't" -> "do", "n't".
            # Offsets are relative to text.
            try:
                spans = list(TreebankWordTokenizer().span_tokenize(text_content))
            except LookupError:
                # Fallback if punkt not found (should be installed)
                continue
                
            if not spans: continue
            
            # To lemmatize correctly we need POS tags.
            # pos_tag expects list of tokens.
            tokens = [text_content[s:e] for s, e in spans]
            pos_tags = nltk.pos_tag(tokens)
            
            for idx, (token, tag) in enumerate(pos_tags):
                # Check 1: Direct match
                candidate = token.lower()
                
                definition = None
                
                # Try simple lookup first
                if candidate in gre_words:
                    definition = gre_words[candidate]
                else:
                    # Lemmatize
                    wn_pos = get_wordnet_pos(tag)
                    lemma = lemmatizer.lemmatize(candidate, pos=wn_pos)
                    if lemma in gre_words:
                        definition = gre_words[lemma]
                    else:
                        # Fallback for "unhappy" -> "happy"
                        # Try stripping prefixes?
                        for prefix in ['un', 'in', 'im', 'dis', 'non', 'Re']:
                            if candidate.startswith(prefix.lower()):
                                root = candidate[len(prefix):]
                                # Check if root is in gre_words? 
                                # Or root lemma?
                                if root in gre_words:
                                    definition = gre_words[root]
                                    break
                                # Try lemmatizing root
                                root_lemma = lemmatizer.lemmatize(root, pos=wn_pos)
                                if root_lemma in gre_words:
                                    definition = gre_words[root_lemma]
                                    break

                if definition:
                    # Found match
                    start, end = spans[idx]
                    
                    # Generate CFI
                    node_cfi = get_element_cfi(text_node)
                    if not node_cfi: continue
                    
                    final_cfi_start = f"{node_cfi}:{start}"
                    final_cfi_end = f"{node_cfi}:{end}"
                    
                    if final_cfi_start in existing_highlights:
                        # Already exists
                        continue
                    
                    # Avoid duplicates locally in this run too?
                    existing_highlights.add(final_cfi_start)
                    
                    # Avoid duplicates? 
                    # Calibre doesn't enforce unique constraints easily.
                    # We print log.
                    
                    print(f"Highlighting '{token}' (Base: {candidate}) at {final_cfi_start}")
                    
                    db.add_annotation(
                        book_id=BOOK_ID,
                        text=token,
                        cfi_start=final_cfi_start,
                        cfi_end=final_cfi_end,
                        spine_index=i,
                        spine_name=spine_name_normalized,
                        notes=f"<b>{candidate}</b>: {definition}",
                        color="blue"
                    )
                    matches_found += 1
                    
        processed_count += 1
    
    print(f"Finished. Added {matches_found} highlights.")

if __name__ == "__main__":
    process_book()
