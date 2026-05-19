#!/usr/bin/env python
"""
Generate gRPC client code from rag-service proto files.
Run this script when the proto files are updated.
"""
import os
import subprocess
import sys
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
RAG_SERVICE_ROOT = PROJECT_ROOT.parent.parent / "rag-service"
PROTO_DIR = RAG_SERVICE_ROOT / "protos"
OUTPUT_DIR = PROJECT_ROOT / "app" / "clients"


def main():
    """Generate gRPC client code."""
    if not PROTO_DIR.exists():
        print(f"Proto directory not found: {PROTO_DIR}")
        print("Make sure rag-service is in the expected location.")
        return 1

    proto_files = list(PROTO_DIR.glob("**/*.proto"))
    if not proto_files:
        print("No .proto files found")
        return 1

    print(f"Found {len(proto_files)} proto files")

    for proto_file in proto_files:
        print(f"Generating code for: {proto_file}")

        cmd = [
            sys.executable, "-m", "grpc_tools.protoc",
            f"--proto_path={PROTO_DIR}",
            f"--python_out={OUTPUT_DIR}",
            f"--pyi_out={OUTPUT_DIR}",
            f"--grpc_python_out={OUTPUT_DIR}",
            str(proto_file),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Error generating {proto_file}:")
            print(result.stderr)
            return 1

    # Fix imports
    fix_imports()

    print("gRPC client generation complete!")
    return 0


def fix_imports():
    """Fix import statements in generated files."""
    for py_file in OUTPUT_DIR.glob("**/*_pb2*.py"):
        content = py_file.read_text()
        original = content

        # Fix imports to use app.clients prefix
        content = content.replace(
            "from rag.v1 import",
            "from app.clients.rag.v1 import"
        )
        content = content.replace(
            "import rag.v1.",
            "import app.clients.rag.v1."
        )

        if content != original:
            py_file.write_text(content)
            print(f"Fixed imports in: {py_file}")


if __name__ == "__main__":
    sys.exit(main())
