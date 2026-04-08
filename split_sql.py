import re

with open("graduation_db(完整但沒分好 copy.sql", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update CREATE TABLE
old_create = """  `category` varchar(20) DEFAULT NULL,
  `time_loc` varchar(255) DEFAULT NULL,"""
new_create = """  `category` varchar(20) DEFAULT NULL,
  `day_of_week` varchar(20) DEFAULT NULL,
  `period` varchar(100) DEFAULT NULL,
  `classroom` varchar(100) DEFAULT NULL,"""
text = text.replace(old_create, new_create)

# 2. Update INSERT INTO statement names
old_insert_into = "(`id`, `academic_year`, `semester`, `course_name`, `teacher`, `credits`, `category`, `time_loc`, `created_at`)"
new_insert_into = "(`id`, `academic_year`, `semester`, `course_name`, `teacher`, `credits`, `category`, `day_of_week`, `period`, `classroom`, `created_at`)"
text = text.replace(old_insert_into, new_insert_into)

# 3. Update the values
def replacer(match):
    prefix = match.group(1) # Everything up to category
    time_loc = match.group(2)
    suffix = match.group(3) # timestamp + closing paren + comma or semicolon
    
    parts = time_loc.split(' ', 2)
    if len(parts) == 3:
        day, period, room = parts
    elif len(parts) == 2:
        day, period = parts
        room = ""
    elif len(parts) == 1:
        day = parts[0]
        period = ""
        room = ""
    else:
        day, period, room = "", "", ""
        
    # handle quotes in classroom safely (though usually none)
    day = day.replace("'", "''")
    period = period.replace("'", "''")
    room = room.replace("'", "''")
    
    return f"{prefix}'{day}', '{period}', '{room}', {suffix}"

# Match format: (...), 'time_loc', 'timestamp'), or );
# The regex must carefully match tuple bodies
pattern = re.compile(
    r"(\(\d+, '[^']+', '[^']+', '[^']+', (?:'[^']+'|NULL), \d+, (?:'[^']+'|NULL), )'([^']+)', ('[^']+'\))"
)
text = pattern.sub(replacer, text)

# Also handle cases where time_loc is NULL if any
text = text.replace("NULL, '202", "NULL, NULL, NULL, '202")

with open("graduation_db_分好版.sql", "w", encoding="utf-8") as f:
    f.write(text)

