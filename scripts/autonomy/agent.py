"""Bounded autonomous engineering agent for GitHub Actions + Amazon Bedrock.

Authentication is delegated to the AWS SDK credential chain. In GitHub Actions this is
expected to be short-lived OIDC/STS credentials, not a static API key. The agent can only
inspect/edit repository files through validated tools.
"""
from __future__ import annotations
import os, subprocess
from pathlib import Path

ROOT = Path.cwd().resolve()
MAX_FILE_BYTES = 200_000
MAX_WRITES = 24
MAX_TURNS = 24
BLOCKED_PREFIXES = (".git/", ".github/workflows/", ".github/actions/")
BLOCKED_FILES = {"AGENTS.md","SECURITY.md","DATA_GOVERNANCE.md","DEFINITION_OF_DONE.md",
                 "EVALUATION_POLICY.md",".github/CODEOWNERS"}
ALLOWED_PREFIXES = ("packages/","services/","connectors/","schemas/","tests/","docs/",
                    "db/migrations/","scripts/autonomy/")
ALLOWED_FILES = {"README.md","ARCHITECTURE.md","pyproject.toml"}

def safe_path(raw: str) -> Path:
    if not raw or raw.startswith("/") or "\x00" in raw:
        raise ValueError("invalid repository path")
    p = Path(raw)
    if any(part in {"..", ".git"} for part in p.parts):
        raise ValueError("path traversal is forbidden")
    normalized = p.as_posix()
    if normalized in BLOCKED_FILES or normalized.startswith(BLOCKED_PREFIXES):
        raise ValueError("path is protected from autonomous modification")
    if normalized not in ALLOWED_FILES and not normalized.startswith(ALLOWED_PREFIXES):
        raise ValueError("path is outside autonomous write scope")
    return (ROOT / p).resolve()

def run(cmd: list[str], timeout: int = 120) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
    return proc.returncode, (proc.stdout + "\n" + proc.stderr).strip()[-20_000:]

def list_files() -> dict:
    code, out = run(["git","ls-files"])
    return {"ok": code == 0, "files": out.splitlines() if code == 0 else out}

def read_file(path: str) -> dict:
    p = safe_path(path)
    if not p.exists(): return {"ok": False, "error": "file not found"}
    data = p.read_text(encoding="utf-8")
    if len(data.encode("utf-8")) > MAX_FILE_BYTES: return {"ok": False, "error": "file exceeds read limit"}
    return {"ok": True, "path": path, "content": data}

def write_file(path: str, content: str) -> dict:
    global writes
    if writes >= MAX_WRITES: return {"ok": False, "error": "write budget exhausted"}
    p = safe_path(path)
    encoded = content.encode("utf-8")
    if len(encoded) > MAX_FILE_BYTES: return {"ok": False, "error": "file exceeds write limit"}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(encoded)
    writes += 1
    return {"ok": True, "path": path, "bytes": len(encoded), "writes_used": writes}

def run_tests() -> dict:
    code, out = run(["python","-m","pytest","-q"], timeout=180)
    return {"ok": code == 0, "exit_code": code, "output": out}

def git_diff() -> dict:
    code, stat = run(["git","diff","--stat"])
    code2, diff = run(["git","diff"], timeout=30)
    return {"ok": code == 0 and code2 == 0, "stat": stat, "diff": diff[-40_000:]}

def git_status() -> dict:
    code, out = run(["git","status","--short","--branch"])
    return {"ok": code == 0, "status": out}

TOOLS = [
 {"toolSpec":{"name":"list_files","description":"List tracked repository files.",
  "inputSchema":{"json":{"type":"object","properties":{},"required":[]}}}},
 {"toolSpec":{"name":"read_file","description":"Read one repository file within the autonomous scope.",
  "inputSchema":{"json":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}}},
 {"toolSpec":{"name":"write_file","description":"Create or replace one text file within the autonomous scope. Never edit protected policy/workflow files.",
  "inputSchema":{"json":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}}},
 {"toolSpec":{"name":"run_tests","description":"Run the repository deterministic unit test suite with pytest.",
  "inputSchema":{"json":{"type":"object","properties":{},"required":[]}}}},
 {"toolSpec":{"name":"git_diff","description":"Inspect the current uncommitted diff.",
  "inputSchema":{"json":{"type":"object","properties":{},"required":[]}}}},
 {"toolSpec":{"name":"git_status","description":"Inspect current git status.",
  "inputSchema":{"json":{"type":"object","properties":{},"required":[]}}}}
]

def tool_call(name: str, args: dict) -> dict:
    try:
        if name=="list_files": return list_files()
        if name=="read_file": return read_file(args["path"])
        if name=="write_file": return write_file(args["path"], args["content"])
        if name=="run_tests": return run_tests()
        if name=="git_diff": return git_diff()
        if name=="git_status": return git_status()
        return {"ok":False,"error":"unknown tool"}
    except Exception as exc:
        return {"ok":False,"error":str(exc)}

def main() -> int:
    global writes
    writes = 0
    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        print("boto3 is required; install the autonomy extra")
        return 2
    task = os.environ.get("GODS_EYE_TASK","").strip()
    if not task:
        print("GODS_EYE_TASK is required")
        return 2
    region = os.environ.get("AWS_REGION","ap-south-1")
    model_id = os.environ.get("GODS_EYE_MODEL_ID","amazon.nova-pro-v1:0")
    client = boto3.client("bedrock-runtime", region_name=region,
                          config=Config(connect_timeout=30, read_timeout=3600, retries={"max_attempts":2}))
    system = """You are the bounded implementation agent for God's Eye World Intelligence.
Follow AGENTS.md, DEFINITION_OF_DONE.md, EVALUATION_POLICY.md and SECURITY.md as mandatory
repository policy. Trust execution, not claims. Work only on the assigned task. Preserve
lawful OSINT/GEOINT boundaries. Never add credentials, private data, surveillance features,
or provider access claims. Do not modify policy files or GitHub workflow files. Prefer the
smallest production-quality change, deterministic contracts, tests, provenance, failure
handling, and documentation. You have no shell tool: use only the supplied repository tools.
Before finishing, inspect the diff and run tests. If the task cannot be safely completed,
make no speculative changes and explain why."""
    messages=[{"role":"user","content":[{"text":f"Assigned bounded task:\n{task}\n\nStart by inspecting the repository and existing contracts. Implement the task completely, then test and review the diff."}]}]
    for _ in range(MAX_TURNS):
        response=client.converse(modelId=model_id,system=[{"text":system}],messages=messages,
            toolConfig={"tools":TOOLS,"toolChoice":{"auto":{}}},
            inferenceConfig={"maxTokens":5000,"temperature":0})
        assistant=response["output"]["message"]
        messages.append(assistant)
        blocks=[b["toolUse"] for b in assistant.get("content",[]) if "toolUse" in b]
        if not blocks:
            print(next((b["text"] for b in assistant.get("content",[]) if "text" in b),"Agent finished."))
            return 0
        results=[]
        for tool in blocks:
            result=tool_call(tool["name"],tool.get("input",{}))
            results.append({"toolResult":{"toolUseId":tool["toolUseId"],"content":[{"json":result}],
                           "status":"success" if result.get("ok") else "error"}})
        messages.append({"role":"user","content":results})
    print("Agent stopped at maximum reasoning/tool turns.")
    return 3

if __name__=="__main__":
    raise SystemExit(main())
