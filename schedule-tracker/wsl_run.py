import subprocess

command = "wsl | python3 deploy.py"
run = subprocess.run(command,shell=True)