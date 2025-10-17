# Wonder Dash

Wonder Dash is a Python-based terminal dashboard for monitoring AWS CloudWatch metrics and local system data.  
It’s built with Rich for live display and runs entirely from the command line.

### What it does
- Streams live AWS CloudWatch metrics (CPU, memory, etc.)
- Shows system-level stats when not connected to AWS
- Designed to look clean in the terminal — not bloated or overcomplicated
- Easy to extend with your own data sources or widgets

### Setup
git clone https://github.com/mjfxjas/wonder_dash.git
cd wonder_dash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m wonder_dash

### Notes
This project started as a way to make a functional CloudWatch monitor without relying on AWS’s web console.  
It’s still being developed and refined, but it runs locally and works with standard AWS credentials.

### License
MIT License © 2025 Jonathan Schimpf
