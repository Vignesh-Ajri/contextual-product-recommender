import subprocess

status_output = subprocess.check_output(['git', 'status', '-s'], universal_newlines=True)

for line in status_output.splitlines():
    if not line.strip():
        continue
    
    state = line[:2]
    # Handle quotes if file path has spaces
    file_path_part = line[3:].strip()
    if file_path_part.startswith('"') and file_path_part.endswith('"'):
        file_path_part = file_path_part[1:-1]
        
    file_path = file_path_part
    if " -> " in file_path:
        file_path = file_path.split(" -> ")[1].strip()
        if file_path.startswith('"') and file_path.endswith('"'):
            file_path = file_path[1:-1]
            
    action = "Update"
    if "??" in state or "A" in state:
        action = "Add"
    elif "D" in state:
        action = "Remove"
        
    msg = f"{action} {file_path}"
    print(f"Processing: {file_path}")
    
    subprocess.run(['git', 'add', '--all', file_path])
    res = subprocess.run(['git', 'commit', '-m', msg])
    if res.returncode == 0:
        subprocess.run(['git', 'push'])
