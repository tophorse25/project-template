import argparse
from collections.abc import Sequence

from analysis.report import generate_markdown_report, read_jsonl, write_report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a merchant-facing product demand report from Reddit JSONL data."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input JSONL file collected from Reddit.",
    )
    parser.add_argument(
        "--product",
        required=True,
        help="Product or keyword being researched.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Markdown report output path.",
    )
    parser.add_argument(
        "--evidence-limit",
        type=int,
        default=10,
        help="Maximum number of evidence links to include.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    records = read_jsonl(args.input)
    markdown = generate_markdown_report(
        records=records,
        product=args.product,
        evidence_limit=args.evidence_limit,
    )
    write_report(markdown=markdown, output_path=args.output)
    print(f"Saved report to {args.output}")


if __name__ == "__main__":
    main()
