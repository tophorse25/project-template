import argparse
from collections.abc import Sequence

from analysis.report import generate_markdown_report, read_jsonl, write_report
from workflows.job_config import load_reddit_crawl_job


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a merchant-facing product demand report from Reddit JSONL data."
    )
    parser.add_argument(
        "--config",
        help="Optional JSON crawl config. Uses output_path as report input and report_path as output.",
    )
    parser.add_argument(
        "--input",
        help="Input JSONL file collected from Reddit.",
    )
    parser.add_argument(
        "--product",
        help="Product or keyword being researched.",
    )
    parser.add_argument(
        "--output",
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
    input_path = args.input
    product = args.product
    output_path = args.output

    if args.config:
        job = load_reddit_crawl_job(args.config)
        input_path = input_path or job.output_path
        product = product or job.product
        output_path = output_path or job.report_path

    if not input_path or not product or not output_path:
        raise SystemExit("--input, --product, and --output are required unless --config supplies them.")

    records = read_jsonl(input_path)
    markdown = generate_markdown_report(
        records=records,
        product=product,
        evidence_limit=args.evidence_limit,
    )
    write_report(markdown=markdown, output_path=output_path)
    print(f"Saved report to {output_path}")


if __name__ == "__main__":
    main()
