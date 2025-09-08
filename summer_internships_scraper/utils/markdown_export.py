import typing as t


def export_to_markdown(jobs: t.List[dict], output_file: str = "README.md"):
    """Generate a simple markdown file with job listings"""

    content = f"""# Summer 2025 internship opportunities

This list gets updated daily.

Posted on refers to the date when the offer was posted on LinkedIn.

## Available positions ({len(jobs)} offers)

"""

    for job in sorted(jobs, key=lambda x: x["posted_date"], reverse=True):
        content += f"""### {job['company_name']}
- **Position:** {job['title']}
- **Location:** {job['location']}
- **Posted on:** {job["posted_date"]}
- [Apply here]({job['url']})

"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
