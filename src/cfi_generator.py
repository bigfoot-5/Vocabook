from ebooklib import epub
from bs4 import BeautifulSoup
import ebooklib

def get_node_index(node):
    """
    Returns the strict CFI index of a node among its siblings.
    Elements = even integers (2, 4, 6...)
    Text/cdata = odd integers (1, 3, 5...)
    """
    parent = node.parent
    if not parent or parent.name == '[document]':
        return None
        
    siblings = []
    for child in parent.contents:
        if isinstance(child, (BeautifulSoup,  ebooklib.epub.EpubHtml)): 
            continue 
        
        if child.name: # Tag
            siblings.append(child)
        elif str(child).strip() or True: 
            # Count logical text nodes
            siblings.append(child)
            
    try:
        preceding_elements = 0
        for sib in siblings:
            if sib is node:
                break
            if sib.name: # Is Element
                preceding_elements += 1
                
        if node.name: # Target is Element
            return (preceding_elements + 1) * 2
        else: # Target is Text
            return (preceding_elements * 2) + 1
            
    except ValueError:
        return None

def calculate_cfi(soup, target_text):
    # Find text node
    # RESTRICTION: Search only within the <body> tag to avoid metadata matches
    search_root = soup.body if soup.body else soup
    
    text_node = search_root.find(string=lambda t: t and target_text in t)
        
    if not text_node:
        return None, None, None
        
    path_steps = []
    current = text_node
    
    # We build path upwards
    while current.parent:
        parent = current.parent
        if parent.name == '[document]':
            # Root element (html) usually index 2
            path_steps.append("2")
            break
            
        idx = get_node_index(current)
        if idx is not None:
            path_steps.append(str(idx))
            
        current = parent
    
    path_steps.reverse()
    path_str = "/" + "/".join(path_steps)
    
    # Calculate offset
    start_offset = text_node.find(target_text)
    end_offset = start_offset + len(target_text)
    
    return path_str, None, (start_offset, end_offset)

def get_element_cfi(element):
    """
    Generates the CFI path for a specific element (e.g. paragraph).
    Returns path string like '/2/4/6'.
    """
    if not element: return None
    
    path_steps = []
    current = element
    
    # We build path upwards
    while current.parent:
        parent = current.parent
        if parent.name == '[document]':
            path_steps.append("2")
            break
            
        idx = get_node_index(current)
        if idx is not None:
            path_steps.append(str(idx))
            
        current = parent
    
    path_steps.reverse()
    return "/" + "/".join(path_steps)
