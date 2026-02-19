
def parse_cfi_to_path(cfi_str):
    """
    Parses a CFI string like 'epubcfi(/2/4/8:0)' into a tuple path.
    Returns: (spine_cfi_index, element_path_tuple)
    Example: '/2/4/8:0' -> (2, (4, 8))
    
    Note: The first part of CFI (/2) identifies the spine item in the package.opf logic.
    Usually (spine_index + 1) * 2.
    """
    if not cfi_str: return None
    
    # Strip epubcfi(...) wrapper if present
    content = cfi_str
    if content.startswith("epubcfi(") and content.endswith(")"):
        content = content[8:-1]
        
    # Remove offset (:123) and assertions ([...])
    # Simple split on ':' to get path vs offset
    # We only care about element path for inclusion check usually
    
    path_part = content.split(':')[0]
    
    # Handle '!' indirection if present (usually /6/4!/4/10) - ignore for now or split?
    # For Calibre bookmarks, it's usually valid simple path.
    
    # Split by '/'
    # Empty string at start because starts with /
    parts = [x for x in path_part.split('/') if x]
    
    # Filter out non-digits (assertions? step indirections?)
    # Valid steps are integers.
    numeric_parts = []
    for p in parts:
        # p might be "4[id]" or just "4"
        # We take the leading number
        import re
        m = re.match(r'^(\d+)', p)
        if m:
            numeric_parts.append(int(m.group(1)))
            
    if not numeric_parts: return None
    
    # Heuristic: Valid spine item CFIs usually start with /2/ (package) then /SpineVal/
    # OR they might just start with /SpineVal/ if relative
    # If first part is 2 (root), take second part as spine item.
    # UNLESS the book actually has a spine item 2 (index 0). 
    # But /2 is reserved for package in OCF. 
    # So if parts[0] == 2, we assume it's the root node, and parts[1] is the spine item.
    
    spine_cfi = numeric_parts[0]
    element_path_start_idx = 1
    
    if spine_cfi == 2 and len(numeric_parts) > 1:
        # Check if it could be /2/4... (std)
        # We assume 2 is root.
        spine_cfi = numeric_parts[1]
        element_path_start_idx = 2
    
    element_path = tuple(numeric_parts[element_path_start_idx:])
    
    return (spine_cfi, element_path)

def extract_numeric_path(cfi_str):
    """
    Extracts purely simple numeric path tuple from CFI, ignoring spine logic.
    Used for raw comparison of relative paths.
    """
    if not cfi_str: return ()
    content = cfi_str
    if content.startswith("epubcfi(") and content.endswith(")"):
        content = content[8:-1]
    
    path_part = content.split(':')[0]
    # Handle indirections if any (split by !) - take last part if relative?
    # Usually bookmarks are absolute (Package!Content).
    # Highlights are usually Content only.
    if '!' in path_part:
        # e.g. /6/14!/4/2/1
        # timestamp logic? no.
        parts = path_part.split('!')
        # We usually want the LAST part for content comparison
        path_part = parts[-1]
        
    parts = [x for x in path_part.split('/') if x]
    numeric_parts = []
    import re
    for p in parts:
        m = re.match(r'^(\d+)', p)
        if m:
            numeric_parts.append(int(m.group(1)))
            
    return tuple(numeric_parts)

def compare_paths(path1, path2):
    """
    Compares two path tuples lexicographically.
    path1, path2: tuples of integers.
    Returns: -1 if p1 < p2, 0 if p1 == p2, 1 if p1 > p2
    
    Logic:
    Compare element by element.
    """
    # Simply python tuple comparison works for lexicographic order matches CFI logic (mostly)
    # /2/4 < /2/6
    # /2/4 < /2/4/1
    
    if path1 < path2: return -1
    if path1 > path2: return 1
    return 0

def is_element_in_range(element_cfi, start_cfi, end_cfi):
    """
    Checks if a given element_cfi is within start_cfi and end_cfi.
    element_cfi: string or parsed tuple? 
    Let's assume caller gets specific element CFI via get_element_cfi
    """
    if not element_cfi: return False
    
    # Parse all
    elem = parse_cfi_to_path(element_cfi)
    start = parse_cfi_to_path(start_cfi)
    end = parse_cfi_to_path(end_cfi)
    
    if not elem: return False
    
    # Unwrap spine index
    e_spine, e_path = elem
    
    # Compare with Start
    if start:
        s_spine, s_path = start
        if e_spine < s_spine: return False
        if e_spine == s_spine:
            # Check path path
            # If element path is "less" than start path?
            # Careful: if Start is /2/4/10 and Element is /2/4, Element contains Start (conceptually parent)
            # But usually we check if Element is AFTER start point.
            # If Element is parent, it contains the start point. Do we include it? 
            # Yes, usually.
            
            # Simple lexicographic:
            # if e_path < s_path: return False 
            # This works for siblings.
            # What if e_path = (4,) and s_path = (4, 10)?
            # (4,) < (4, 10) is True.
            # So it returns False (out of rang).
            # But (4,) is the parent of (4,10). The parent starts BEFORE the child.
            # So if we want strictly "between bookmarks", and the bookmark is IN the paragraph.
            # The paragraph *starts* before the bookmark.
            # Should we include the paragraph?
            # Ideally yes, we process the paragraph but maybe ignore text before offset.
            # But for "Bulk Injection", if we include the parent, we inject.
            
            # Allow parents:
            # If s_path starts with e_path (e is parent of s), we include it.
            
            is_parent = (len(e_path) < len(s_path)) and (s_path[:len(e_path)] == e_path)
            if not is_parent and e_path < s_path:
                return False
                
    # Compare with End
    if end:
        en_spine, en_path = end
        if e_spine > en_spine: return False
        if e_spine == en_spine:
            # If element is AFTER end point
            # if e_path > en_path: return False
            
            # If e is parent of end marker?
            # End marker is inside e.
            # So e *ends* after end marker? No, e contains end marker.
            # We should probably include it.
            
            is_parent = (len(e_path) < len(en_path)) and (en_path[:len(e_path)] == e_path)
            if not is_parent and e_path > en_path:
                return False
                
    return True
