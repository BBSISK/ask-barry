"""Split Markdown documents into heading-aware chunks for retrieval.

Each chunk keeps:
  - the heading breadcrumb it sits under (e.g. "Wall Inspector > CI/CD"),
    which is prepended to the text so the chunk makes sense on its own;
  - its source (repo, path, commit) and a GitHub link to the exact heading,
    so answers can cite precisely where the information came from.

Sections longer than max_chars are split on paragraph boundaries (never
inside a fenced code block), with one paragraph of overlap between pieces.
Size is measured in characters (~4 characters per token for English).
"""
import hashlib
import re
from dataclasses import asdict, dataclass

DEFAULT_MAX_CHARS = 2000   # ~500 tokens
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
EMPTY_LINK_RE = re.compile(r"\[\s*\]\([^)]*\)")   # left behind by stripped badge images


@dataclass
class Chunk:
    chunk_id: str
    repo: str
    path: str
    heading: str        # breadcrumb, e.g. "Title > Setup > Docker"
    anchor: str         # GitHub heading anchor ("" for text before the first heading)
    url: str            # link to the file (and heading) on GitHub
    commit_sha: str
    text: str           # breadcrumb + section text, ready to index
    content_hash: str   # changes only when the text changes (for re-indexing later)

    def to_dict(self):
        return asdict(self)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def github_slug(heading):
    """Approximate GitHub's heading anchor: lowercase, drop punctuation, spaces -> '-'."""
    text = re.sub(r"`|\*\*|__|\*|_(?=\W)|(?<=\W)_", "", heading)       # strip inline markup
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)                # [text](link) -> text
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def plain_heading(heading):
    """Heading text for breadcrumbs: links -> their text, no backticks/bold markers."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)
    text = re.sub(r"`|\*\*|__", "", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_markdown(text):
    """Remove noise that hurts retrieval: HTML comments, images/badges, empty links."""
    text = HTML_COMMENT_RE.sub("", text)
    text = IMAGE_RE.sub("", text)
    text = EMPTY_LINK_RE.sub("", text)
    return text


def split_sections(markdown):
    """Yield (level, title, body_lines) for each heading section.

    Text before the first heading is yielded with level 0 and title "".
    Lines that look like headings inside fenced code blocks are ignored.
    """
    sections = []
    level, title, body = 0, "", []
    in_fence = False
    for line in markdown.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            body.append(line)
            continue
        m = None if in_fence else HEADING_RE.match(line)
        if m:
            sections.append((level, title, body))
            level, title, body = len(m.group(1)), m.group(2).strip(), []
        else:
            body.append(line)
    sections.append((level, title, body))
    return sections


def split_paragraphs(lines):
    """Group lines into paragraphs on blank lines, keeping code fences intact."""
    paragraphs, current, in_fence = [], [], False
    for line in lines:
        if FENCE_RE.match(line):
            in_fence = not in_fence
        if not line.strip() and not in_fence:
            if current:
                paragraphs.append("\n".join(current))
                current = []
        else:
            current.append(line)
    if current:
        paragraphs.append("\n".join(current))
    return paragraphs


def pack_paragraphs(paragraphs, max_chars):
    """Pack paragraphs into pieces <= max_chars, overlapping by one paragraph.

    A single paragraph longer than max_chars is hard-split on line or
    character boundaries so no piece ever exceeds the limit.
    """
    units = []
    for p in paragraphs:
        if len(p) <= max_chars:
            units.append(p)
        else:
            units.extend(_hard_split(p, max_chars))

    pieces, current = [], []
    for unit in units:
        candidate = current + [unit]
        if current and len("\n\n".join(candidate)) > max_chars:
            pieces.append("\n\n".join(current))
            overlap = current[-1]
            current = [overlap, unit] if len(overlap) + len(unit) + 2 <= max_chars else [unit]
        else:
            current = candidate
    if current:
        pieces.append("\n\n".join(current))
    return pieces


def _hard_split(text, max_chars):
    pieces, current = [], ""
    for line in text.splitlines():
        while len(line) > max_chars:
            if current:
                pieces.append(current)
                current = ""
            pieces.append(line[:max_chars])
            line = line[max_chars:]
        if current and len(current) + 1 + len(line) > max_chars:
            pieces.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        pieces.append(current)
    return pieces


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def chunk_markdown(markdown, repo, path, url, commit_sha="", max_chars=DEFAULT_MAX_CHARS):
    """Split one Markdown document into Chunk objects."""
    if max_chars < 200:
        raise ValueError("max_chars must be at least 200")

    chunks = []
    breadcrumb = []            # list of (level, title)
    slug_counts = {}
    for level, title, body in split_sections(clean_markdown(markdown)):
        anchor = ""
        if level:
            breadcrumb = [(lv, t) for lv, t in breadcrumb if lv < level] + [(level, plain_heading(title))]
            base = github_slug(title)
            n = slug_counts.get(base, 0)
            slug_counts[base] = n + 1
            anchor = base if n == 0 else f"{base}-{n}"

        paragraphs = split_paragraphs(body)
        if not paragraphs:
            continue                      # heading with no content of its own
        heading = " > ".join(t for _, t in breadcrumb)
        prefix = f"{heading}\n\n" if heading else ""
        budget = max_chars - len(prefix)
        if budget < 100:                  # absurdly long breadcrumb: keep only the last heading
            heading = breadcrumb[-1][1] if breadcrumb else ""
            prefix = f"{heading[:100]}\n\n" if heading else ""
            budget = max_chars - len(prefix)

        for piece in pack_paragraphs(paragraphs, budget):
            text = prefix + piece
            index = len(chunks)
            chunks.append(Chunk(
                chunk_id=f"{repo}:{path}#{index}",
                repo=repo,
                path=path,
                heading=heading,
                anchor=anchor,
                url=f"{url}#{anchor}" if anchor else url,
                commit_sha=commit_sha,
                text=text,
                content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
            ))
    return chunks
