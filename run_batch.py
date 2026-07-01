import subprocess
import sys
import os

os.environ["PYTHONUTF8"] = "1"
result = subprocess.run(
    [sys.executable, "batch_process.py"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace"
)
print("STDOUT:")
print(result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout)
print("\nSTDERR:")
print(result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)
print(f"\nExit code: {result.returncode}")
