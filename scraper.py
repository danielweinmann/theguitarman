#!/usr/bin/env python3
import os
import re
import time
from datetime import datetime

import feedparser
import requests
from markdownify import markdownify as md
from slugify import slugify

BLOG_FEED_URL = "https://theguitarman.blogspot.com/feeds/posts/default"
OUTPUT_DIR = "posts"
MAX_RESULTS_PER_PAGE = 25
REQUEST_DELAY = 0.5


def fetch_all_posts():
    posts = []
    url = f"{BLOG_FEED_URL}?max-results={MAX_RESULTS_PER_PAGE}"

    while url:
        print(f"Fetching: {url}")
        feed = feedparser.parse(url)

        if feed.bozo and not feed.entries:
            print(f"Error fetching feed: {feed.bozo_exception}")
            break

        posts.extend(feed.entries)
        print(f"  Found {len(feed.entries)} entries (total: {len(posts)})")

        url = None
        for link in feed.feed.get("links", []):
            if link.get("rel") == "next":
                url = link.get("href")
                break

        if url:
            time.sleep(REQUEST_DELAY)

    return posts


def extract_post_id(entry):
    entry_id = entry.get("id", "")
    match = re.search(r"post-(\d+)", entry_id)
    return match.group(1) if match else None


def fetch_comments(post_id):
    if not post_id:
        return []

    url = f"https://theguitarman.blogspot.com/feeds/{post_id}/comments/default"

    try:
        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            return []
        return feed.entries
    except Exception as e:
        print(f"  Error fetching comments for {post_id}: {e}")
        return []


def parse_datetime(date_string):
    try:
        dt = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        return dt
    except (ValueError, AttributeError):
        return None


def generate_folder_name(dt, title):
    date_prefix = dt.strftime("%Y-%m-%d-%H-%M")

    if title and title.strip():
        slug = slugify(title, max_length=50)
        return f"{date_prefix}-{slug}"
    else:
        return date_prefix


def html_to_markdown(html_content):
    if not html_content:
        return ""
    return md(html_content, heading_style="ATX", strip=["script", "style"])


def format_comment_date(date_string):
    dt = parse_datetime(date_string)
    if dt:
        return dt.strftime("%Y-%m-%d %H:%M")
    return date_string


def process_post(entry, output_base):
    title = entry.get("title", "").strip()
    published = entry.get("published", "")
    content = ""

    if "content" in entry and entry["content"]:
        content = entry["content"][0].get("value", "")
    elif "summary" in entry:
        content = entry.get("summary", "")

    dt = parse_datetime(published)
    if not dt:
        print(f"  Skipping post with invalid date: {published}")
        return None

    folder_name = generate_folder_name(dt, title)
    year = dt.strftime("%Y")
    folder_path = os.path.join(output_base, year, folder_name)

    os.makedirs(folder_path, exist_ok=True)

    markdown_content = html_to_markdown(content)

    index_path = os.path.join(folder_path, "index.md")
    with open(index_path, "w", encoding="utf-8") as f:
        if title:
            f.write(f"# {title}\n\n")
        f.write(markdown_content.strip())
        f.write("\n")

    post_id = extract_post_id(entry)
    if post_id:
        time.sleep(REQUEST_DELAY)
        comments = fetch_comments(post_id)

        if comments:
            comments_path = os.path.join(folder_path, "comments.md")
            with open(comments_path, "w", encoding="utf-8") as f:
                f.write("# Comments\n\n")

                for i, comment in enumerate(comments):
                    author = comment.get("author_detail", {}).get("name", "Anonymous")
                    comment_date = comment.get("published", "")
                    comment_content = ""

                    if "content" in comment and comment["content"]:
                        comment_content = comment["content"][0].get("value", "")
                    elif "summary" in comment:
                        comment_content = comment.get("summary", "")

                    formatted_date = format_comment_date(comment_date)
                    comment_md = html_to_markdown(comment_content)

                    f.write(f"## {author} - {formatted_date}\n\n")
                    f.write(comment_md.strip())
                    f.write("\n\n")

                    if i < len(comments) - 1:
                        f.write("---\n\n")

    return folder_path


def main():
    print("Fetching all posts from the blog...")
    posts = fetch_all_posts()
    print(f"\nTotal posts found: {len(posts)}")

    if not posts:
        print("No posts found. Exiting.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"\nProcessing posts...")
    for i, entry in enumerate(posts, 1):
        title = entry.get("title", "(untitled)")[:50]
        print(f"[{i}/{len(posts)}] {title}")

        try:
            folder = process_post(entry, OUTPUT_DIR)
            if folder:
                print(f"  → {folder}")
        except Exception as e:
            print(f"  Error: {e}")

    print(f"\nDone! Posts saved to ./{OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
