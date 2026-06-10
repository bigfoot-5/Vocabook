
def parse_cfi_to_path(cfi_str):
    """
    Parses a CFI string like 'epubcfi(/2/4/8:0)' into a tuple path.
    Returns: (spine_cfi_index, element_path_tuple)
    Example: '/2/4/8:0' -> (2, (4, 8))
    
    Note: The first part of CFI (/2) identifies the spine item in the package.opf logic.
    Usually (spine_index + 1) * 2.
    """
    if not cfi_str: return None
    
    content = cfi_str
    if content.startswith("epubcfi(") and content.endswith(")"):
        content = content[8:-1]
        

    
    path_part = content.split(':')[0]
    

    

    parts = [x for x in path_part.split('/') if x]
    

    numeric_parts = []
    for p in parts:

        import re
        m = re.match(r'^(\d+)', p)
        if m:
            numeric_parts.append(int(m.group(1)))
            
    if not numeric_parts: return None
    

    
    spine_cfi = numeric_parts[0]
    element_path_start_idx = 1
    
    if spine_cfi == 2 and len(numeric_parts) > 1:

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

    if '!' in path_part:

        parts = path_part.split('!')

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
    
    elem = parse_cfi_to_path(element_cfi)
    start = parse_cfi_to_path(start_cfi)
    end = parse_cfi_to_path(end_cfi)
    
    if not elem: return False
    
    e_spine, e_path = elem
    
    if start:
        s_spine, s_path = start
        if e_spine < s_spine: return False
        if e_spine == s_spine:
            
            
            
            is_parent = (len(e_path) < len(s_path)) and (s_path[:len(e_path)] == e_path)
            if not is_parent and e_path < s_path:
                return False
                
    if end:
        en_spine, en_path = end
        if e_spine > en_spine: return False
        if e_spine == en_spine:
            
            
            is_parent = (len(e_path) < len(en_path)) and (en_path[:len(e_path)] == e_path)
            if not is_parent and e_path > en_path:
                return False
                
    return True
