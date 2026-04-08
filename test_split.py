import re

with open("graduation_db(完整但沒分好 copy.sql", "r", encoding="utf-8") as f:
    text = f.read()

# Match INSERT statements
# Format: ('114', '上學期', '...', '...', 2, '...', 'time_loc', 'time')
# Let's just find all time_loc strings using a simple regex since it's the second to last string
inserts = re.findall(r"\(\d+, '[^']+', '[^']+', '[^']+', (?:'[^']+'|NULL), \d+, '[^']+', '([^']+)', '[^']+'\)", text)
for t in inserts:
    parts = t.split(' ')
    if len(parts) < 3:
        pass # print(f"Bad split: {repr(t)}")

bad_splits = [t for t in inserts if len(t.split(' ', 2)) != 3]
print(f"Total time_locs found: {len(inserts)}")
print(f"Bad splits count: {len(bad_splits)}")
for b in bad_splits[:10]:
    print(repr(b))
