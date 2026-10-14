import sys
import json
import time
import re
import unicodedata
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# ==============================================================================
# Path Setup & Project Imports
# ==============================================================================
# Add project root to sys.path (find the directory containing db_structs.py)
_root = Path(__file__).resolve().parent
while _root.parent != _root:
    if (_root / "db_structs.py").exists():
        if str(_root) not in sys.path:
            sys.path.append(str(_root))
        break
    _root = _root.parent

from db_structs import Circle, is_to_add

PATH_EVENT = Path(__file__).parent
PATH_CIRCLES_JSON = PATH_EVENT / "circles.json"
NAME = PATH_EVENT.name


# ==============================================================================
# HTTP & Cache Helpers
# ==============================================================================
def retrieve_soup_fetch_if_needed(
    url: str,
    file_name: str = "raw.html",
    fallback_url: str | None = None,
    encoding: str | None = None,
    headers: dict[str, str] | None = None,
) -> BeautifulSoup:
    """Retrieve BeautifulSoup from local cache, or fetch from URL with retry/fallback."""
    html_path = PATH_EVENT / file_name
    if not html_path.exists():
        print(f"Raw HTML file not found, fetching from {url} ...")
        req_headers = {"User-Agent": "Mozilla/5.0"}
        if headers:
            req_headers.update(headers)

        response = None
        for attempt in range(5):
            try:
                response = requests.get(url, headers=req_headers, timeout=30)
                if response.status_code == 200:
                    break
                if fallback_url is not None:
                    print(
                        f"Primary URL returned {response.status_code}; trying fallback {fallback_url} ..."
                    )
                    response = requests.get(fallback_url, headers=req_headers, timeout=30)
                    if response.status_code == 200:
                        break
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(1 + attempt)

        if response is None or response.status_code != 200:
            status = response.status_code if response else "No response"
            raise RuntimeError(f"Failed to retrieve data from {url}, status code: {status}")

        html_path.write_bytes(response.content)

    with html_path.open("rb") as f:
        return BeautifulSoup(f, "html.parser", from_encoding=encoding)


def remove_wayback_prefix(url: str) -> str:
    """Strip Wayback Machine URL prefix (e.g. //web.archive.org/web/20120101000000/)."""
    return re.sub(r"^(?:https?:)?//web\.archive\.org/web/\d+(?:[a-z]{2}_)?/", "", url)


# ==============================================================================
# Text Cleaning & Normalization
# ==============================================================================
def sanitize_string(s: str) -> str:
    """Strip edge whitespace and collapse internal whitespace."""
    s = s.strip()
    return re.sub(r"[\s\n\t]+", " ", s)


# Common character substitutions for fuzzy Japanese text matching
SUBSTITUTIONS = {
    # Tildes / prolonged sound marks / dashes
    "～": "〜",
    "~": "〜",
    "ー": "-",
    "－": "-",
    "−": "-",
    "‐": "-",
    # Fullwidth symbols
    "＆": "&",
    "＋": "+",
    "！": "!",
    "？": "?",
    "（": "(",
    "）": ")",
    "［": "[",
    "］": "]",
    "．": ".",
    "’": "'",
    "`": "'",
    "･": ".",
    "・": ".",
    "·": ".",
    "　": " ",
    "\u200b": "",  # zero-width space
}

# Manual alias mapping: secondary/ternary name -> canonical primary name
# Use this for non-trivial aliases, joint artist names, simplified Chinese, or typos
SPECIAL_MATCHES: dict[str, str] = {
}


def normalize_for_match(text: str) -> str:
    """Normalize text using NFKC, custom substitutions, whitespace stripping, and casefold."""
    text = unicodedata.normalize("NFKC", text)
    for src, dst in SUBSTITUTIONS.items():
        text = text.replace(src, dst)
    return re.sub(r"\s+", "", text).casefold()


def ensure_unicity(texts: list[str]) -> list[str]:
    """Deduplicate strings preserving order, ignoring case and whitespace differences."""
    seen: set[str] = set()
    result: list[str] = []
    for text in texts:
        norm = normalize_for_match(text)
        if norm not in seen:
            seen.add(norm)
            result.append(text)
    return result


def is_name_match(
    query_name: str,
    target_name: str,
    special_matches: dict[str, str] | None = None,
) -> bool:
    """Check if query_name matches target_name (exact, via SPECIAL_MATCHES, or as group member)."""
    q_norm = normalize_for_match(query_name)
    t_norm = normalize_for_match(target_name)
    if q_norm == t_norm:
        return True

    # Check special mappings (bidirectional)
    mapping = special_matches if special_matches is not None else SPECIAL_MATCHES
    if mapping.get(query_name) == target_name or mapping.get(target_name) == query_name:
        return True
    if normalize_for_match(mapping.get(query_name, "")) == t_norm:
        return True

    # Strip parenthetical annotations (e.g. "CircleName (Author)")
    q_unannotated = re.sub(r"[（(][^（）()]*[）)]$", "", query_name)
    if q_norm != normalize_for_match(q_unannotated):
        if normalize_for_match(q_unannotated) == t_norm:
            return True

    # Check if target is a joint/group unit (e.g. "CircleA & CircleB", "CircleA vs CircleB", "CircleAとCircleB")
    group_members = re.split(r"[&+/|x]|vs", t_norm)
    group_members.extend(part for m in list(group_members) for part in re.split(r"と", m))
    return any(q_norm == m for m in group_members if m)


def extract_match_keys(name: str) -> set[str]:
    """Generate index lookup keys for a circle name (including composite sub-units)."""
    norm = normalize_for_match(name)
    keys = {norm}
    sub_members = re.split(r"[&+/|x]|vs", norm)
    keys.update(sub_members)
    keys.update(part for m in sub_members for part in re.split(r"と", m))
    return {k for k in keys if k}


# ==============================================================================
# Circle Dictionary Helper Data Class
# ==============================================================================
class CircleRecord:
    """Internal representation of a circle entry during extraction and merging."""

    def __init__(
        self,
        name: str,
        position: str = "",
        pen_name: str = "",
        links: list[str] | None = None,
        description: list[str] | None = None,
    ):
        self.name = name
        self.position = position
        self.pen_name = pen_name
        self.links: list[str] = links or []
        self.description: list[str] = description or []
        self.aliases: list[str] = [name]

    def add_links(self, new_links: list[str]):
        self.links.extend(new_links)

    def add_alias(self, alias: str):
        if alias and alias not in self.aliases:
            self.aliases.append(alias)

    def to_circle_struct(self) -> Circle:
        return Circle(
            position=self.position if is_to_add(self.position) else None,
            description=self.description if is_to_add(self.description) else None,
            links=ensure_unicity(self.links) if is_to_add(self.links) else None,
            aliases=ensure_unicity(self.aliases),
            pen_names=[self.pen_name] if is_to_add(self.pen_name) else None,
        )


class CircleRegistry:
    """Manages the reference list of circles and indexing for secondary/ternary matching."""

    def __init__(self):
        self.records: list[CircleRecord] = []
        self._name_index: dict[str, list[int]] = {}

    def add(self, record: CircleRecord) -> int:
        idx = len(self.records)
        self.records.append(record)
        for key in extract_match_keys(record.name):
            self._name_index.setdefault(key, []).append(idx)
        return idx

    def find_match_index(
        self,
        name: str,
        special_matches: dict[str, str] | None = None,
    ) -> int | None:
        """Find matching circle index using indexed lookup first, fallback to linear scan."""
        norm = normalize_for_match(name)
        candidates = self._name_index.get(norm)
        if candidates is not None:
            for idx in candidates:
                if is_name_match(name, self.records[idx].name, special_matches):
                    return idx

        # Fallback to checking all records (e.g. for special mappings or composite sub-units)
        for idx, rec in enumerate(self.records):
            if is_name_match(name, rec.name, special_matches):
                return idx
        return None

    def export_circles(self) -> list[Circle]:
        return [rec.to_circle_struct() for rec in self.records]


# ==============================================================================
# Source Parsers (Adapt these functions for each event)
# ==============================================================================
def parse_primary_source(registry: CircleRegistry):
    """
    Primary Source: Canonical reference circle list.
    Every circle participating in the event should originate here.
    """
    official_pages = [
        "https://web.archive.org/web/20170504223846/http://project-d.biz/tohosaiji/circle_list.html",
    ]
    for page_idx, page_url in enumerate(official_pages):
        soup = retrieve_soup_fetch_if_needed(
            page_url,
            file_name=f"raw_official_{page_idx}.html",
            encoding="cp932",
        )
        tables = soup.find_all("table")
        # Target table with "参加イベント" in headers
        target_table = None
        for t in tables:
            first_row = t.find("tr")
            if first_row and "参加イベント" in first_row.get_text():
                target_table = t
                break

        if not target_table:
            target_table = tables[2] if len(tables) > 2 else (tables[0] if tables else None)

        rows = target_table.find_all("tr") if target_table else []
        if not rows:
            continue

        header_cells = [sanitize_string(th.get_text(strip=True)) for th in rows[0].find_all(["th", "td"])]
        name_col = header_cells.index("サークル名") if "サークル名" in header_cells else 0
        pen_col = header_cells.index("ペンネーム") if "ペンネーム" in header_cells else 1
        event_col = header_cells.index("参加イベント") if "参加イベント" in header_cells else 2
        pos_col = header_cells.index("配置番号") if "配置番号" in header_cells else 3

        page_count = 0
        for row in rows[1:]:
            cells = row.find_all("td", recursive=False)
            if len(cells) <= max(name_col, pen_col, event_col, pos_col):
                continue

            event = sanitize_string(cells[event_col].get_text(strip=True))
            if "境界から視えた外界-至-" not in event:
                continue

            circle_name = sanitize_string(cells[name_col].get_text(strip=True))
            pen_name = sanitize_string(cells[pen_col].get_text(strip=True))
            position = sanitize_string(cells[pos_col].get_text(strip=True))

            # Header or empty check
            if not circle_name or "サークル名" in circle_name:
                continue

            # Extract URLs across all cells (URL, Pixiv, Twitter)
            links = [
                remove_wayback_prefix(str(a["href"]))
                for a in row.find_all("a", href=True)
            ]

            record = CircleRecord(
                name=circle_name,
                position=position,
                pen_name=pen_name,
                links=links,
            )
            registry.add(record)
            page_count += 1

        print(f"Found {page_count} circles in official page {page_idx + 1}")

    print(f"Total reference circles: {len(registry.records)}")


# def parse_secondary_source(registry: CircleRegistry):
#     """
#     Secondary Source (Optional): Supplementary website (e.g. THBWiki, catalog mirror).
#     Matches against reference circles to enrich links, pen names, or aliases.
#     """
#     secondary_urls = [
#     ]
#     matched_count = 0
#     for sec_idx, sec_url in enumerate(secondary_urls):
#         soup = retrieve_soup_fetch_if_needed(
#             sec_url,
#             file_name=f"raw_secondary_{sec_idx}.html",
#             fallback_url=f"https://web.archive.org/web/2/{sec_url}",
#         )
#         for table in soup.find_all("table", class_="wikitable"):
#             headers = [th.get_text(strip=True) for th in table.find_all("th")]
#             if "制作方" not in headers:
#                 continue
#             circle_col = headers.index("制作方")
#             link_col = headers.index("官网") if "官网" in headers else -1

#             for row in table.find_all("tr"):
#                 cols = row.find_all("td", recursive=False)
#                 if not cols or len(cols) <= circle_col:
#                     continue

#                 sec_circle_name = sanitize_string(cols[circle_col].get_text(strip=True))
#                 if not sec_circle_name:
#                     continue

#                 sec_links = (
#                     [
#                         remove_wayback_prefix(str(a["href"]))
#                         for a in cols[link_col].find_all("a", href=True)
#                     ]
#                     if link_col >= 0
#                     else []
#                 )

#                 match_idx = registry.find_match_index(sec_circle_name)
#                 if match_idx is not None:
#                     matched_rec = registry.records[match_idx]
#                     matched_rec.add_links(sec_links)
#                     matched_rec.add_alias(sec_circle_name)
#                     matched_count += 1

#     print(f"Merged {matched_count} secondary entries")


# def parse_ternary_source(registry: CircleRegistry):
#     """
#     Ternary Source (Optional): Hardcoded layout map dictionary or external floor map data.
#     Provides booth spaces / positions for matching circles.
#     """
#     # Structure: { Section: { PositionNumber: CircleName } }
#     circles_dict: dict[str, dict[str, str]] = {
#         # "A": {
#         #     "01": "Circle Name 1",
#         #     "02": "Circle Name 2",
#         # },
#     }

#     matched_count = 0
#     for section, positions in circles_dict.items():
#         for pos_num, circle_name in positions.items():
#             full_position = f"{section}{pos_num}"
#             match_idx = registry.find_match_index(circle_name)
#             if match_idx is not None:
#                 matched_rec = registry.records[match_idx]
#                 matched_rec.position = full_position
#                 matched_count += 1
#             else:
#                 print(f"[Ternary Unmatched] {full_position}: '{circle_name}'")

#     print(f"Merged {matched_count} ternary positions")


# ==============================================================================
# Main Orchestrator
# ==============================================================================
def main():
    """Create circles.json by orchestrating primary, secondary, and ternary sources."""
    print(f"Retrieving circles information for {NAME} ...")

    registry = CircleRegistry()

    # 1. Primary Source: populate reference list
    parse_primary_source(registry)

    # # 2. Secondary Source: enrich links & aliases
    # parse_secondary_source(registry)

    # # 3. Ternary Source: assign positions
    # parse_ternary_source(registry)

    # 4. Export & Save
    circles = registry.export_circles()
    with open(PATH_CIRCLES_JSON, "w", encoding="utf-8") as f:
        json.dump([c.get_json() for c in circles], f, ensure_ascii=False, indent=2)

    print(f"Saved {len(circles)} circles to {PATH_CIRCLES_JSON}")


if __name__ == "__main__":
    main()
