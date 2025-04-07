from pathlib import Path


WORK_DIR = Path(__file__).parent
COMMANDS_PATH = WORK_DIR / "commands"
COMMANDS_ENDPOINT_FILENAME = "main.py"
COMMANDS_PROPS_FILENAME = "props.yaml"
COMMANDS_PATTERN = "[!__]*"
