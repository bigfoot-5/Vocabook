from src.cfi_utils import parse_cfi_to_path, is_element_in_range

h_cfi = "/2/4/2/84/1:153"
start_cfi = "epubcfi(/16/2/4/2/10/1:369)"
end_cfi = "epubcfi(/16/2/4/2/70/1:104)"

print(f"H: {h_cfi}")
print(f"Start: {start_cfi}")
print(f"End: {end_cfi}")

parsed_h = parse_cfi_to_path(h_cfi)
parsed_start = parse_cfi_to_path(start_cfi)

print(f"Parsed H: {parsed_h}")
print(f"Parsed Start: {parsed_start}")

in_range = is_element_in_range(h_cfi, start_cfi, end_cfi)
print(f"In Range? {in_range}")
