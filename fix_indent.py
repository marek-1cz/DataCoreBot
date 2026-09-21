with open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(len(lines)):
    if 'elif s.get("approved") is True:' in lines[i]:
        # Indent the next 7 lines by 4 spaces
        for j in range(1, 8):
            if i+j < len(lines):
                # Only add if it's not already indented correctly
                if lines[i+j].startswith('                        import json'):
                    lines[i+j] = lines[i+j].replace('                        ', '                            ', 1)
                elif lines[i+j].startswith('                        state = '):
                    lines[i+j] = lines[i+j].replace('                        ', '                            ', 1)
                elif lines[i+j].startswith('                        state_str'):
                    lines[i+j] = lines[i+j].replace('                        ', '                            ', 1)
                elif lines[i+j].startswith('                        h = '):
                    lines[i+j] = lines[i+j].replace('                        ', '                            ', 1)
                elif lines[i+j].startswith('                        if h !='):
                    lines[i+j] = lines[i+j].replace('                        ', '                            ', 1)
                elif lines[i+j].startswith('                            last_state'):
                    lines[i+j] = lines[i+j].replace('                            ', '                                ', 1)
                elif lines[i+j].startswith('                            yield f"'):
                    lines[i+j] = lines[i+j].replace('                            ', '                                ', 1)

with open('main.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
