from calibre.library import db
db = db('/Users/karthiktalluri/Calibre Library').new_api

print(f"Connected to library. Found {len(db.all_book_ids())} books.")
book_id = 13
formats = db.formats(book_id)
print(f"Formats for Book {book_id}: {formats}")
import zipfile
import xml.etree.ElementTree as ET
import re

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    text = re.sub(cleanr, '', raw_html)
    return text

def read_epub(path):
    with zipfile.ZipFile(path, 'r') as epub:
        container_xml = epub.read('META-INF/container.xml')
        root = ET.fromstring(container_xml)
        opf_path = root.find('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile').attrib['full-path']
        
        opf_data = epub.read(opf_path)
        opf_root = ET.fromstring(opf_data)
        
        ns = {'opf': 'http://www.idpf.org/2007/opf'}
        
        manifest = {}
        for item in opf_root.findall('.//opf:item', ns):
            manifest[item.attrib['id']] = item.attrib['href']
            
        spine = opf_root.find('.//opf:spine', ns)
        count = 0
        for itemref in spine.findall('.//opf:itemref', ns):
            if count >= 2: break # Just read 2 chapters/sections
            idref = itemref.attrib['idref']
            href = manifest.get(idref)
            
            if href:
                if '/' in opf_path:
                    base_dir = opf_path.rsplit('/', 1)[0]
                    full_href = f"{base_dir}/{href}"
                else:
                    full_href = href
                
                try:
                    content = epub.read(full_href).decode('utf-8')
                    text = clean_html(content)
                    print(f"\n--- Section: {href} ---\n")
                    print(text[:1000] + "...") # Print first 1000 chars
                    count += 1
                except Exception as e:
                    print(f"Could not read {full_href}: {e}")

def highlight_epub(src_path, dest_path, target_text, replacement_html):
    with zipfile.ZipFile(src_path, 'r') as zin, zipfile.ZipFile(dest_path, 'w') as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.endswith(('.xhtml', '.html', '.htm')):
                try:
                    content = data.decode('utf-8')
                    if target_text in content:
                        print(f"Found match in {item.filename}")
                        content = content.replace(target_text, replacement_html)
                        data = content.encode('utf-8')
                except UnicodeDecodeError:
                    pass # binary check skipped
            zout.writestr(item, data)

if formats:
    epub_path = db.format(book_id, 'EPUB', as_path=True)
    if epub_path:
        
        output_path = '/Users/karthiktalluri/Desktop/Coding/Vocabook/modified_book.epub'
        target = "Simon &amp; Schuster"
        replacement = "<span style='background-color: yellow;'>Simon &amp; Schuster</span>"
        
        print(f"Attempting to highlight '{target}'...")
        highlight_epub(epub_path, output_path, target, replacement)
        
        print("Updating Calibre library...")
        db.add_format(book_id, 'EPUB', output_path, replace=True)
        print("Done! You can verify the highlight in the Calibre viewer.")