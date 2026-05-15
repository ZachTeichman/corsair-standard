from __future__ import annotations

import argparse
import json
from typing import Optional, Sequence

from .analyzer import analyze_docx


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="corsair")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Analyze a DOCX resume against corsair_v1.")
    analyze.add_argument("path", help="Absolute or relative path to the DOCX file.")
    analyze.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    analyze.add_argument("--render", action="store_true", help="Validate final page count by rendering DOCX to PDF.")

    normalize = subparsers.add_parser("normalize", help="Normalize a DOCX resume toward the canonical layout.")
    normalize.add_argument("path", help="Absolute or relative path to the input DOCX file.")
    normalize.add_argument("--output", required=True, help="Path to write the normalized DOCX file.")
    normalize.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")

    compile_doc = subparsers.add_parser("compile", help="Rebuild a DOCX resume into the canonical layout.")
    compile_doc.add_argument("path", help="Absolute or relative path to the input DOCX file.")
    compile_doc.add_argument("--output", required=True, help="Path to write the compiled DOCX file.")
    compile_doc.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    compile_doc.add_argument("--render", action="store_true", help="Validate final page count by rendering DOCX to PDF.")

    compile_blocks = subparsers.add_parser("compile-blocks", help="Rebuild a DOCX by cloning canonical paragraph blocks.")
    compile_blocks.add_argument("path", help="Absolute or relative path to the input DOCX file.")
    compile_blocks.add_argument("--output", required=True, help="Path to write the compiled DOCX file.")
    compile_blocks.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    compile_blocks.add_argument("--render", action="store_true", help="Validate final page count by rendering DOCX to PDF.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        result = analyze_docx(args.path, render=args.render)
        if args.pretty:
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps(result))
        return 0

    if args.command == "normalize":
        from .normalize import normalize_docx

        result = normalize_docx(args.path, args.output)
        if args.pretty:
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps(result))
        return 0

    if args.command == "compile":
        from .block_compiler import compile_docx_from_blocks

        result = compile_docx_from_blocks(args.path, args.output, render=args.render)
        if args.pretty:
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps(result))
        return 0

    if args.command == "compile-blocks":
        from .block_compiler import compile_docx_from_blocks

        result = compile_docx_from_blocks(args.path, args.output, render=args.render)
        if args.pretty:
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps(result))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2
