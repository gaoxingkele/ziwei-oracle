"""
Download and transform fortune stick (灵签) data into standardized JSON format.

Sources:
- 观音灵签: https://github.com/steventango/guan-yin-ling-qian (zh-cn data)
- 诸葛神算: https://github.com/sealdice/draw (sealdice_draw/诸葛神算.json)
- 黄大仙灵签: https://www.51chouqian.com/huangdaxianlingqian/

Standard format per sign:
{
    "number": int,
    "level": str,      # 吉凶: 上上签/上签/中签/下签/下下签 etc.
    "poem": str,       # 签诗
    "interpretation": str,  # 解签
    "story": str       # 典故 (if available)
}
"""

import json
import os
import re
import time
import requests

OUTDIR = os.path.dirname(os.path.abspath(__file__))


def build_guanyin():
    """Download and transform 观音灵签 (100 signs) from GitHub."""
    print("=== Building 观音灵签 ===")
    base_url = "https://raw.githubusercontent.com/steventango/guan-yin-ling-qian/main/data"
    results = []

    for i in range(1, 101):
        # Use zh-cn (simplified Chinese) version
        url = f"{base_url}/zh-cn/{i}.json"
        try:
            r = requests.get(url, timeout=15)
            r.encoding = 'utf-8'
            data = json.loads(r.text)
        except Exception as e:
            print(f"  Failed to fetch sign {i}: {e}")
            continue

        # Also get raw version for the traditional poem text
        raw_url = f"{base_url}/raw/{i}.json"
        try:
            r2 = requests.get(raw_url, timeout=15)
            r2.encoding = 'utf-8'
            raw_data = json.loads(r2.text)
        except Exception:
            raw_data = {}

        # Parse level from "第X籤" field, e.g. "第一上签", "第二下签（中签 ）"
        level_raw = data.get("第X籤", "")
        level = extract_level(level_raw)

        # Poem: use 籤詩版本二 (simplified) from zh-cn
        poem = data.get("籤詩版本二", "")
        # Also try raw traditional version 1
        if not poem and raw_data:
            poem = raw_data.get("籤詩版本一", raw_data.get("籤詩版本二", ""))

        # Interpretation: combine 詩意 + 解曰
        interpretation_parts = []
        shi_yi = data.get("詩意", "")
        if shi_yi:
            interpretation_parts.append(shi_yi)
        jie_yue = data.get("解曰", "")
        if jie_yue:
            interpretation_parts.append(jie_yue)
        interpretation = "\n".join(interpretation_parts)

        # Story: use 籤詩故事一
        story = data.get("籤詩故事一", "")
        # Clean up whitespace
        if story:
            story = re.sub(r'\t+', '', story).strip()

        # 古人 (classical reference)
        ancient = data.get("古人", "")

        sign = {
            "number": i,
            "level": level,
            "poem": poem.strip(),
            "interpretation": interpretation.strip(),
            "story": f"【{ancient}】\n{story}" if ancient and story else (story or ancient or ""),
        }
        results.append(sign)

        if i % 20 == 0:
            print(f"  Fetched {i}/100")

    outpath = os.path.join(OUTDIR, "guanyin.json")
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  Saved {len(results)} signs to {outpath}")
    return results


def extract_level(text):
    """Extract fortune level from text like '第一上签', '第二下签（中签 ）'."""
    # Check for parenthesized level override
    paren = re.search(r'[（(](.*?)[）)]', text)
    if paren:
        inner = paren.group(1).strip()
        if '上上' in inner:
            return '上上签'
        elif '下下' in inner:
            return '下下签'
        elif '中上' in inner:
            return '中上签'
        elif '中下' in inner:
            return '中下签'
        elif '上' in inner:
            return '上签'
        elif '中' in inner:
            return '中签'
        elif '下' in inner:
            return '下签'

    # Direct extraction
    if '上上' in text:
        return '上上签'
    elif '下下' in text:
        return '下下签'
    elif '中上' in text:
        return '中上签'
    elif '中下' in text:
        return '中下签'
    elif '上签' in text or '上簽' in text:
        return '上签'
    elif '中签' in text or '中簽' in text:
        return '中签'
    elif '下签' in text or '下簽' in text:
        return '下签'
    return text.strip()


def build_zhuge():
    """Download and transform 诸葛神算 (384 signs) from GitHub."""
    print("=== Building 诸葛神算 ===")
    url = 'https://raw.githubusercontent.com/sealdice/draw/main/sealdice_draw/%E8%AF%B8%E8%91%9B%E7%A5%9E%E7%AE%97.json'
    r = requests.get(url, timeout=30)
    r.encoding = 'utf-8'
    data = json.loads(r.text)

    # Find the main data key (诸葛神算)
    main_key = [k for k in data.keys() if not k.startswith('_')][0]
    entries = data[main_key]
    print(f"  Found {len(entries)} raw entries")

    results = []
    for i, entry in enumerate(entries):
        parsed = parse_zhuge_entry(entry, i + 1)
        if parsed:
            results.append(parsed)

    outpath = os.path.join(OUTDIR, "zhuge.json")
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  Saved {len(results)} signs to {outpath}")
    return results


def parse_zhuge_entry(text, fallback_num):
    """Parse a single 诸葛神算 entry.

    Format example:
    第〇〇一签（功名利禄）
    【上上签】乾宫 乾变大有（乾九五）
    签诗：天门一挂榜...解签：大吉...
    """
    lines = text.strip().split('\n')

    # Extract number
    num_match = re.search(r'第([〇一二三四五六七八九零]+)签', text)
    if num_match:
        number = chinese_num_to_int(num_match.group(1))
    else:
        number = fallback_num

    # Extract level
    level_match = re.search(r'【(.+?)】', text)
    level = level_match.group(1) if level_match else ""

    # Extract poem (签诗：...解签：)
    poem_match = re.search(r'签诗[：:](.+?)(?:解签|$)', text, re.DOTALL)
    poem = poem_match.group(1).strip().rstrip('.。') if poem_match else ""

    # Extract interpretation (解签：...)
    interp_match = re.search(r'解签[：:](.+?)$', text, re.DOTALL)
    interpretation = interp_match.group(1).strip() if interp_match else ""

    # Extract theme from parentheses in first line
    theme_match = re.search(r'签[（(](.+?)[）)]', text)
    story = theme_match.group(1) if theme_match else ""

    return {
        "number": number,
        "level": level,
        "poem": poem,
        "interpretation": interpretation,
        "story": story,
    }


def chinese_num_to_int(s):
    """Convert Chinese number string like '〇〇一' to integer 1."""
    mapping = {
        '〇': '0', '零': '0',
        '一': '1', '二': '2', '三': '3', '四': '4', '五': '5',
        '六': '6', '七': '7', '八': '8', '九': '9',
    }
    digits = ''.join(mapping.get(c, c) for c in s)
    try:
        return int(digits)
    except ValueError:
        return 0


def build_huangdaxian():
    """Build 黄大仙灵签 (100 signs) by scraping from website."""
    print("=== Building 黄大仙灵签 ===")
    results = []

    for i in range(1, 101):
        url = f"https://www.51chouqian.com/huangdaxianlingqian/{i}.html"
        try:
            r = requests.get(url, timeout=15)
            r.encoding = 'utf-8'
            html = r.text
        except Exception as e:
            print(f"  Failed to fetch sign {i}: {e}")
            continue

        sign = parse_huangdaxian_html(html, i)
        results.append(sign)

        if i % 20 == 0:
            print(f"  Fetched {i}/100")
        # Be polite to the server
        time.sleep(0.3)

    outpath = os.path.join(OUTDIR, "huangdaxian.json")
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  Saved {len(results)} signs to {outpath}")
    return results


def parse_huangdaxian_html(html, number):
    """Parse 黄大仙灵签 HTML page to extract sign data."""
    # Extract level (吉凶) - usually in format like "上上" or "中吉" etc.
    level = ""
    level_match = re.search(r'签[：:]\s*第\d+签\s*(\S+?)签', html)
    if not level_match:
        level_match = re.search(r'<[^>]*>(\S{1,4}签)</[^>]*>', html)
    if not level_match:
        # Try another pattern: look for 上上/上吉/中吉/中平/下下 etc.
        level_match = re.search(r'([上中下]{1,2}[上中下吉平凶]{0,1}签)', html)
    if level_match:
        level = level_match.group(1)

    # Extract poem (签诗)
    poem = ""
    # Pattern: look for the 4-line poem
    poem_match = re.search(r'签[诗詩][：:]\s*(.*?)(?:<|解[签簽])', html, re.DOTALL)
    if not poem_match:
        # Try to find poem between specific tags
        poem_match = re.search(r'灵签求得第\d+枝[：:]\s*(.*?)(?:<br|</)', html, re.DOTALL)
    if poem_match:
        poem = clean_html(poem_match.group(1))

    # Alternative: look for the classic poem format
    if not poem:
        # Look for "灵签求得第X枝" pattern
        poem_match = re.search(r'(灵签求得第\d+枝[：:].*?)(?:</p|</div|<br)', html, re.DOTALL)
        if poem_match:
            poem = clean_html(poem_match.group(1))

    # Extract interpretation (解签)
    interpretation = ""
    interp_match = re.search(r'解[签簽][：:]\s*(.*?)(?:</p|</div|<h|签[诗詩]故事)', html, re.DOTALL)
    if interp_match:
        interpretation = clean_html(interp_match.group(1))

    # Extract story (典故)
    story = ""
    story_match = re.search(r'(?:典故|故事|古人)[：:]\s*(.*?)(?:</p|</div|<h[1-6])', html, re.DOTALL)
    if story_match:
        story = clean_html(story_match.group(1))

    return {
        "number": number,
        "level": level,
        "poem": poem.strip(),
        "interpretation": interpretation.strip(),
        "story": story.strip(),
    }


def clean_html(text):
    """Remove HTML tags and clean whitespace."""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&[a-z]+;', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


if __name__ == '__main__':
    build_guanyin()
    build_zhuge()
    build_huangdaxian()

    # Clean up temp files
    raw_path = os.path.join(OUTDIR, 'zhuge_raw.json')
    if os.path.exists(raw_path):
        os.remove(raw_path)
    print("\nDone! All files generated.")
