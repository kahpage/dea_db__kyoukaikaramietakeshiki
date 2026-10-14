import sys
import json
from pathlib import Path
from typing import Any
import requests
from bs4 import BeautifulSoup
import lxml
import re
import unicodedata
from urllib.parse import urljoin, urlparse

# Add project root to sys.path (find the directory containing db_structs.py)
_root = Path(__file__).resolve().parent
while _root.parent != _root:
    if (_root / "db_structs.py").exists():
        if str(_root) not in sys.path:
            sys.path.append(str(_root))
        break
    _root = _root.parent

from db_structs import (
    Medium,
    Circle,
    Event,
    EventGroup,
    Source,
    ReliabilityTypes,
    OriginTypes,
    Location,
    is_to_add,
)

PATH_EVENT = Path(__file__).parent
PATH_CIRCLES_JSON = PATH_EVENT / "circles.json"
NAME = PATH_EVENT.name


import time


def retrieve_soup_fetch_if_needed(
    url: str,
    file_name: str = "raw.html",
    fallback_url: str | None = None,
    encoding: str | None = None,
) -> BeautifulSoup:
    """Retrieve a page, using a fallback URL when the primary source rejects the request."""
    html_path = PATH_EVENT / file_name
    if not html_path.exists():
        print(f"Raw HTML file not found, fetching from {url} ...")
        headers = {"User-Agent": "Mozilla/5.0"}
        response = None
        for attempt in range(5):
            try:
                response = requests.get(url, headers=headers, timeout=30)
                if response.status_code == 200:
                    break
                if fallback_url is not None:
                    print(
                        f"Primary source returned {response.status_code}; fetching from fallback ..."
                    )
                    response = requests.get(fallback_url, headers=headers, timeout=30)
                    if response.status_code == 200:
                        break
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(1 + attempt)

        if response is None or response.status_code != 200:
            status = response.status_code if response else "No response"
            raise Exception(
                f"Failed to retrieve data from {url}, status code: {status}"
            )
        html_path.write_bytes(response.content)
    with html_path.open("rb") as f:
        return BeautifulSoup(f, "lxml", from_encoding=encoding)


def sanitize_string(s: str) -> str:
    s = s.strip()
    s = re.sub(r"[\s\n\t]+", " ", s)
    return s


FULLWIDTH = {
    "０": "0",
    "１": "1",
    "２": "2",
    "３": "3",
    "４": "4",
    "５": "5",
    "６": "6",
    "７": "7",
    "８": "8",
    "９": "9",
    "Ａ": "A",
    "Ｂ": "B",
    "Ｃ": "C",
    "Ｄ": "D",
    "Ｅ": "E",
    "Ｆ": "F",
    "Ｇ": "G",
    "Ｈ": "H",
    "Ｉ": "I",
    "Ｊ": "J",
    "Ｋ": "K",
    "Ｌ": "L",
    "Ｍ": "M",
    "Ｎ": "N",
    "Ｏ": "O",
    "Ｐ": "P",
    "Ｑ": "Q",
    "Ｒ": "R",
    "Ｓ": "S",
    "Ｔ": "T",
    "Ｕ": "U",
    "Ｖ": "V",
    "Ｗ": "W",
    "Ｘ": "X",
    "Ｙ": "Y",
    "Ｚ": "Z",
    "ａ": "a",
    "ｂ": "b",
    "ｃ": "c",
    "ｄ": "d",
    "ｅ": "e",
    "ｆ": "f",
    "ｇ": "g",
    "ｈ": "h",
    "ｉ": "i",
    "ｊ": "j",
    "ｋ": "k",
    "ｌ": "l",
    "ｍ": "m",
    "ｎ": "n",
    "ｏ": "o",
    "ｐ": "p",
    "ｑ": "q",
    "ｒ": "r",
    "ｓ": "s",
    "ｔ": "t",
    "ｕ": "u",
    "ｖ": "v",
    "ｗ": "w",
    "ｘ": "x",
    "ｙ": "y",
    "ｚ": "z",
}
SUBSTITUTIONS = {
    "～": "〜",
    "~": "〜",
    "ー": "-",
    "－": "-",
    "−": "-",
    "＆": "&",
    "＋": "+",
    "　": " ",
    "-": "-",
    "\\u3000": " ",
    "！": "!",
    "．": ".",
    "’": "'",
    "`": "'",
    "･": ".",
    "・": ".",
    "·": ".",
}
SUBSTITUTIONS_ALL = {}
SUBSTITUTIONS_ALL.update(FULLWIDTH)
SUBSTITUTIONS_ALL.update(SUBSTITUTIONS)


def is_in_with_subst(str1: str, bigstr: str) -> bool:
    return normalize_for_match(str1) in normalize_for_match(bigstr)


def normalize_for_match(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    for key, value in SUBSTITUTIONS_ALL.items():
        text = text.replace(key, value)
    text = text.replace("\u200b", "")
    return re.sub(r"\s+", "", text).casefold()


def is_equal_with_subst(str1: str, str2: str) -> bool:
    return normalize_for_match(str1) == normalize_for_match(str2)


SPECIAL_MATCHES = {
    "卵たつぷり": "卵たっぷり",
    "ペーたんずラボ": "ぺーたんず ラボ",
    "久幸繙文&幻想ノ郷茶": "久幸繙文＆幻想ノ郷茶話会",
    "ラストオーダーはとつ": "ラストオーダーはとつぜんに",
    "ちょこびるる": "ちょこびゐる",
    "まくろびおていか": "まくろびおてぃか",
    "142本目の紅いリアト": "142本目の紅いリアトリス",
    "Forest306 & Sing, R.S": "Forest306 & Sing， R. Sing!",
    "桃のカンツメ": "桃のカンヅメ",
    "妹音〜Poteto Sou": "妹音〜Poteto Sound〜",
    "荒御灵": "荒御霊",
    "Forest306Sing, R. Sing！": "Forest306 & Sing， R. Sing!",
    "よいむつ": "ちょいむつ",
    "かくれざとう": "Ennui Girl’s Talk",
    "ゆめいろごろも1pos": "たんしょくごろも",
    "ゆめかばん白上さん家": "サクサク",
    "heri／hodie": "てきとーに",
    "TUMENECO四面楚歌いよかん。ヘルメットが直せませんななつめぐり": "冷たい人比良が直せない予感。",
    "TUMENECO": "冷たい人比良が直せない予感。",
    "Lunatico_fEs": "Lunatico",
    "K-waves LABO-LIFE.JP": "ゴツまさ倶楽部",
}


def is_equal_or_group_member(str1: str, str2: str) -> bool:
    target = normalize_for_match(str1)
    if target == normalize_for_match(str2):
        return True
    if SPECIAL_MATCHES.get(str1) == str2 or SPECIAL_MATCHES.get(str2) == str1:
        return True
    annotated_target = re.sub(r"[（(][^（）()]*[）)]$", "", str1)
    if target != normalize_for_match(annotated_target):
        target = normalize_for_match(annotated_target)
    normalized_group = normalize_for_match(str2)
    group_members = re.split(r"[&+/]|vs", normalized_group)
    group_members.extend(
        part for member in list(group_members) for part in re.split(r"と", member)
    )
    return any(target == member for member in group_members)


def get_rts5_match_keys(name: str) -> set[str]:
    normalized_name = normalize_for_match(name)
    keys = {normalized_name}
    group_members = re.split(r"[&+/]|vs", normalized_name)
    keys.update(group_members)
    keys.update(part for member in group_members for part in re.split(r"と", member))
    return {key for key in keys if key}


def ensure_unicity(texts: list[str]) -> list[str]:
    """Ensure that the list of texts contains unique entries, ignoring case and substitutions."""
    seen = set()
    unique_texts = []
    for text in texts:
        normalized_text = text.lower()
        for key, value in SUBSTITUTIONS_ALL.items():
            normalized_text = normalized_text.replace(key, value)
        if normalized_text not in seen:
            seen.add(normalized_text)
            unique_texts.append(text)
    return unique_texts


def remove_wayback_prefix(url: str) -> str:
    return re.sub(r"^(?:https?:)?//web\.archive\.org/web/\d+(?:[a-z]{2}_)?/", "", url)

def remove_hidden_spans(value: str) -> str:
    return re.sub(r"<span[^>]*>.*?</span>", "", value, flags=re.DOTALL)


def main():
    """Create circles.json"""
    print(f"Retrieving circles information for {NAME} ...")
    circles: list[Circle] = []

    # Official source
    circles_info = []
    official_pages = [
        "https://web.archive.org/web/20101125182439/http://kyoukai.warabies.com/list.htm",
    ]
    for page_index, page_url in enumerate(official_pages):
        official_soup = retrieve_soup_fetch_if_needed(
            page_url,
            f"raw_official_{page_index}.html",
            encoding="cp932",
        )
        official_table = official_soup.find("table")
        official_rows = official_table.find_all("tr") if official_table else []
        page_circle_count = 0
        for row in official_rows:
            cells = row.find_all("td", recursive=False)
            if len(cells) < 2:
                continue
            position = ""
            circle_name = sanitize_string(cells[0].get_text(strip=True))
            pen_name = sanitize_string(cells[1].get_text(strip=True))
            link_cell = cells[0]

            if "サークル名" in circle_name or not circle_name:
                continue
            links = [
                remove_wayback_prefix(str(a["href"]))
                for a in link_cell.find_all("a", href=True)
            ]
            page_circle_count += 1

            circles_info.append({
                "circle_name": circle_name,
                "circle_penname": pen_name,
                "position": position,
                "links": links,
                "description": [],
            })
        print(f"Found {page_circle_count} circles in official page {page_index + 1}")

    print(f"Found {len(circles_info)} circles across {len(official_pages)} official source pages")

    for info in circles_info:
        info["links"] = ensure_unicity(info["links"])

    official_name_index: dict[str, list[int]] = {}
    for index, info in enumerate(circles_info):
        for key in get_rts5_match_keys(info["circle_name"]):
            official_name_index.setdefault(key, []).append(index)

    # Secondary source:
    secondary_links = [
        "https://thwiki.cc/%E5%B1%95%E4%BC%9A%E4%BD%9C%E5%93%81%E5%88%97%E8%A1%A8?e=%E5%A2%83%E7%95%8C%E6%89%80%E8%A7%81%E5%88%B0%E7%9A%84%E5%A4%96%E7%95%8C%231"
    ]
    secondary_match_count = 0
    for secondary_index, secondary_url in enumerate(secondary_links):
        secondary_soup = retrieve_soup_fetch_if_needed(
            secondary_url,
            f"raw_secondary_{secondary_index}.html",
            f"https://web.archive.org/web/2/{secondary_url}",
        )
        for table in secondary_soup.find_all("table", class_="wikitable"):
            headers = [th.get_text(strip=True) for th in table.find_all("th")]
            if "制作方" not in headers:
                continue
            circle_col = headers.index("制作方")
            link_col = headers.index("官网") if "官网" in headers else -1
            for row in table.find_all("tr"):
                cols = row.find_all("td", recursive=False)
                if not cols or len(cols) <= circle_col:
                    continue
                circle_name = cols[circle_col].get_text(strip=True)
                links = (
                    [
                        remove_wayback_prefix(str(a["href"]))
                        for a in cols[link_col].find_all("a", href=True)
                    ]
                    if link_col >= 0
                    else []
                )
                candidate_indices = official_name_index.get(
                    normalize_for_match(circle_name),
                    range(len(circles_info)),
                )
                for index in candidate_indices:
                    if is_equal_or_group_member(
                        circle_name, circles_info[index]["circle_name"]
                    ):
                        circles_info[index]["links"].extend(links)
                        secondary_match_count += 1
                        break

    print(f"Merged {secondary_match_count} secondary rows")

    # Ternary source:
    # Manually from https://web.archive.org/web/20250112160330/http://www.green.dti.ne.jp/maisan/gensoukyou/image/kyoukaikaramietakeshiki.pdf

    circles_dict: dict[str, dict[str, str]] = {} # Section: {pos_num: circle_name}

    # === 部 ===
    circles_dict["部"] = {
        "01": "honey blue",
        "02": "負け橙組",
        "03": "東ガル会",
        "04": "彼之庵",
        "05": "しめさばダイナミック",
        "06": "schwarzwald",
        "07": "ナナシノ十字星団",
        "08": "e-Paranoia",
        "09": "電派絵師団",
        "10": "Lapin Asile",
        "11": "Quarter Iceshop",
        "12": "TUNA-3d",
        "13": "たんしょくごろも",
        "14": "結神亭",
        "15": "匿名天体",
        # "16": "実行委員会用予備スペース"
        "17,18": "冷たい人比良が直せない予感。",
        # "19": "実行委員会用予備スペース"
        "20": "赤色バニラ",
        "21": "ギロチン銀座",
        "22": "8bit canvas",
        "23": "四方山",
        "24": "airdrop",
        "25": "アトリエ桃源郷",
        "26": "sugilight",
        "27": "小豆粥",
        "28": "鏡花水月",
        "29": "RED-SIGHT",
        "30": "アンニュイ赤蛸",
        "31,32": "世界秘封病学会",
    }
    
    # === 楽 ===
    circles_dict["楽"] = {
        "01": "snowfield",
        "02": "あとカフェラテ",
        "03": "アルフ·ライラ",
        "04": "漁火狐火",
        "05": "直VI-DAZE",
        "06": "オリエント鈍行",
        "07": "オレンジペコ",
        "08": "五花八門",
        "09": "Grass Doll",
        "10": "少女リップルズ",
        "11": "ひゃほい帝国",
        "12": "中規模夢想",
        "13": "からしめんたいこ",
        "14": "雪月華",
        "15": "HurrySense",
        "16": "ぐちょまぜ猫貴族",
        # "17": "実行委員会用予備スペース"
        "18": "りべるて",
        "19": "するめぇか。",
        "20": "ペーたんずラボ",
        "21": "二丁目租界",
        "22": "世田谷ボロ市",
        "23": "YUGUPETTI＊",
        "24": "Tsubame yado",
        "25": "SnowGale",
        "26": "Atmosphere theory",
        "27": "豆屋",
        "28": "MEMENT MORI",
        "29": "ハテノハテ星雲",
        "30": "ICBM",
        "31": "桔梗の花の咲くところ",
        "32": "わすれな部屋",
    }
    
    # === 倶 ===
    circles_dict["倶"] = {
        "01": "サクサク",
        "02": "ジョナサン",
        "03": "桜花月間",
        "04": "優戯",
        "05": "海豚の猫拳",
        "06": "春日郷想",
        "07": "無音工房",
        "08": "青茶會談",
        "09": "久幸繙文&幻想ノ郷茶",
        "10": "星空亭",
        "11": "偽薬籠中之月",
        "12": "七月のむじな",
        "13": "卵たつぷり",
        "14": "暮れ雨。",
        "15": "遊星",
        # "16": "準備会スペース",
        "17": "Imitation Room",
        "18": "遙かなる根の国",
        "19": "Wildish...",
        "20": "ラストオーダーはとつ",
        "21": "ネクロユニオン",
        "22": "電気は送れません。",
        "23": "三食角砂糖",
        "24": "とある荒野の休憩所。",
        "25": "アイネクライネ",
        "26": "ぴぽいこしっと",
        "27": "石薔薇十字団",
        "28": "Magic Melancholy",
        "29": "またぽとうほうしぶ",
        "30": "コ館★",
        "31": "ちょこびるる",
        "32": "明日やろう。",
    }
    
    # === 封 ===
    circles_dict["封"] = {
        "01": "天気輪の柱",
        "02": "へひゃい!!",
        "03": "CRiMary",
        "04": "256Diver",
        "05": "まくろびおていか",
        "06": "GKW",
        "07": "Nerd-Goods.com",
        "08": "k@!",
        "09": "草枕文庫",
        "10": "櫻川",
        "11": "ジャム工房",
        "12": "てきとーに",
        "13": "残酷綿棒",
        "14": "RIGHT+LIGHT",
        "15": "零式エルゴ領域",
        "16": "火照るパン",
        "17": "御祭長屋",
        "18": "Rhythm Five",
        "19": "夏色緑茶",
        "20": "雨具文庫",
        "21": "書肆「鰻」",
        "22": "乱蹴ハンス島",
        "23": "つくね書房",
        "24": "川の流れに身を任せ",
        "25": "和服亭",
        "26": "PALMLAP",
        "27": "142本目の紅いリアト",
        "28": "雨降らしの竜",
        "29": "ハスミ書房",
        "30": "あかれんが",
        "31": "BYKエンタープライズ",
        "32": "姫上家",
    }

    # === 秘 ===
    circles_dict["秘"] = {
        "01": "ゴツまさ倶楽部",
        "02": "Forest306 & Sing, R.S",
        "03": "荒御霊",
        "04": "UnLimited Questions",
        "05": "天狗ノ舞",
        "06": "Siestail",
        "07": "まかろに☆けちゃっぷ",
        "08": "Alice Music",
        "09": "UNVALANCE",
        "10": "KARASHIC RECORDS",
        "11": "桃のカンツメ",
        "12": "乃藤悟志",
        "13": "秋の七草",
        "14": "ふじつぼ",
        "15": "トップ派のハット卿",
        "16": "折葉坂三番地",
        "17": "NORTH LEAVE",
        "18": "碧礫亭",
        "19": "極彩色",
        "20": "友毒屋",
        "21": "sweater-girl",
        "22": "THE WATER DUCTS",
        "23": "ゐた·せくすありす",
        "24": "妹音〜Poteto Sou",
        "25": "有限産業すきま風",
        "26": "軍手艦隊",
        "27": "にゃんこの目",
        # "28": "実行委員会用予備スペース"
        # "29": "実行委員会用予備スペース"
        # "30": "実行委員会用予備スペース"
        "31": "うんちく商事",
        "32": "Water.Club.",
        "33": "Ennui Girl's Talk",
        "34": "命の限り好き勝手。",
        "35": "華胥の永眠",
        "36": "ちょいむつ",
        "37": "街角麻婆豆",
        "38": "onionclub",
        "39": "Lunatico",
        "40": "やぁい!",
    }

    ternary_match_count = 0
    for section in circles_dict:
        for pos_num, circle_name in circles_dict[section].items():
            position = f"{section}{pos_num}"
            candidate_indices = official_name_index.get(
                normalize_for_match(circle_name),
                range(len(circles_info)),
            )
            for index in candidate_indices:
                if is_equal_or_group_member(
                    circle_name, circles_info[index]["circle_name"]
                ):
                    circles_info[index]["position"] = position
                    ternary_match_count += 1
                    break

    print(f"Merged {ternary_match_count} ternary positions")

    for info in circles_info:
        circles.append(
            Circle(
                position=info["position"] if is_to_add(info["position"]) else None,
                description=info["description"]
                if is_to_add(info["description"])
                else None,
                links=ensure_unicity(info["links"])
                if is_to_add(info["links"])
                else None,
                aliases=[info["circle_name"]],
                pen_names=[info["circle_penname"]]
                if is_to_add(info["circle_penname"])
                else None,
            )
        )
    # circles.sort(key=lambda c: c.position or "")

    # Save the extracted circle information to a JSON file
    with open(PATH_CIRCLES_JSON, "w", encoding="utf-8") as f:
        json.dump([c.get_json() for c in circles], f, ensure_ascii=False, indent=2)
    print(f"Saved {len(circles)} circles to {PATH_CIRCLES_JSON}")


if __name__ == "__main__":
    main()
