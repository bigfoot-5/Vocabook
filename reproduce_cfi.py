from bs4 import BeautifulSoup
from src.cfi_generator import calculate_cfi
import sys

# Simulated HTML structure based on user's description
# Assuming standard EPUB structure where text is inside <p> tags
html_content = """
<html>
  <head>
    <title>activation - Test Book</title>
  </head>
  <body>
    <div>
      <p>Some previous text.</p>
      <p>On activation each morning Charles’ first duty was to check his master’s travel arrangements for the day.</p>
      <p>His last task of the previous evening had also been to check his master’s travel arrangements for the coming day, so he was entirely aware his master had no travel arrangements, and would be remaining at home as he had for the preceding 2,230 days.</p>
    </div>
  </body>
</html>
"""

target = "activation"

def test_cfi():
    soup = BeautifulSoup(html_content, 'html.parser')
    print("--- HTML Structure ---")
    print(soup.prettify())
    print("\n--- Target ---")
    print(f"Word: '{target}'")
    
    # Test strict body search (should skip title)
    # Note: Logic not yet changed, so it might fail or find title depending on current impl
    # We call it without context now, as we removed that requirement
    path_str, _, offsets = calculate_cfi(soup, target)
    
    if path_str:
        full_cfi = f"epubcfi(/6{path_str}:{offsets[0]})" # Assuming spine index 6
        print(f"\nGeneratred Path: {path_str}")
        print(f"Offsets: {offsets}")
        print(f"Full Simulated CFI: {full_cfi}")
    else:
        print("\nFailed to generate CFI")

if __name__ == "__main__":
    test_cfi()
