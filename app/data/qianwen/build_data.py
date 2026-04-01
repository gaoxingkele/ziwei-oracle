"""
Download and transform fortune stick data into standardized JSON format.
"""
import json
import os
import re
import time
import requests

OUTDIR = os.path.dirname(os.path.abspath(__file__))


def chinese_num_to_int(s):
    mapping = {'〇':'0','零':'0','一':'1','二':'2','三':'3','四':'4',
               '五':'5','六':'6','七':'7','八':'8','九':'9'}
    return int(''.join(mapping.get(c, c) for c in s))


def extract_guanyin_level(text):
    """Extract level from e.g. '第一上签', '第二下签（中签 ）'."""
    # Check parenthesized override first
    m = re.search(r'[（(]([^）)]+)[）)]', text)
    if m:
        text = m.group(1).strip()
    for pat in ['上上', '下下', '中上', '中下', '上', '中', '下']:
        if pat in text:
            return pat + '签'
    return text.strip()


def build_guanyin():
    """观音灵签 (100 signs)"""
    print("=== Building guanyin.json ===")
    base = "https://raw.githubusercontent.com/steventango/guan-yin-ling-qian/main/data/zh-cn"
    results = []
    for i in range(1, 101):
        try:
            r = requests.get(f"{base}/{i}.json", timeout=15)
            r.encoding = 'utf-8'
            d = json.loads(r.text)
        except Exception as e:
            print(f"  SKIP {i}: {e}")
            continue

        level_field = d.get("\u7c64X\u7c64", d.get("第X籤", ""))
        level = extract_guanyin_level(level_field)

        poem = d.get("\u7c64\u8a69\u7248\u672c\u4e8c", d.get("籤詩版本二", "")).strip()
        shi_yi = d.get("\u8a69\u610f", d.get("詩意", "")).strip()
        jie_yue = d.get("\u89e3\u66f0", d.get("解曰", "")).strip()
        interp = "\n".join(p for p in [shi_yi, jie_yue] if p)
        story_raw = d.get("\u7c64\u8a69\u6545\u4e8b\u4e00", d.get("籤詩故事一", ""))
        story = re.sub(r'\t+', '', story_raw).strip() if story_raw else ""
        ancient = d.get("\u53e4\u4eba", d.get("古人", "")).strip()
        if ancient and story:
            story = f"【{ancient}】\n{story}"
        elif ancient:
            story = ancient

        results.append({
            "number": i,
            "level": level,
            "poem": poem,
            "interpretation": interp,
            "story": story,
        })
        if i % 25 == 0:
            print(f"  {i}/100")

    path = os.path.join(OUTDIR, "guanyin.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  -> {len(results)} signs saved")


def build_zhuge():
    """诸葛神算 (384 signs)"""
    print("=== Building zhuge.json ===")
    url = 'https://raw.githubusercontent.com/sealdice/draw/main/sealdice_draw/%E8%AF%B8%E8%91%9B%E7%A5%9E%E7%AE%97.json'
    r = requests.get(url, timeout=30)
    r.encoding = 'utf-8'
    data = json.loads(r.text)
    main_key = [k for k in data if not k.startswith('_')][0]
    entries = data[main_key]
    print(f"  Found {len(entries)} raw entries")

    results = []
    for idx, text in enumerate(entries):
        num_m = re.search(r'第([〇一二三四五六七八九零]+)签', text)
        number = chinese_num_to_int(num_m.group(1)) if num_m else idx + 1

        level_m = re.search(r'【(.+?)】', text)
        level = level_m.group(1) if level_m else ""

        theme_m = re.search(r'签[（(](.+?)[）)]', text)
        story = theme_m.group(1) if theme_m else ""

        poem_m = re.search(r'签诗[：:](.+?)(?:\.?解签|$)', text, re.DOTALL)
        poem = poem_m.group(1).strip().rstrip('.。') if poem_m else ""

        interp_m = re.search(r'解签[：:](.+?)$', text, re.DOTALL)
        interpretation = interp_m.group(1).strip() if interp_m else ""

        results.append({
            "number": number,
            "level": level,
            "poem": poem,
            "interpretation": interpretation,
            "story": story,
        })

    path = os.path.join(OUTDIR, "zhuge.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  -> {len(results)} signs saved")


def clean_html(text):
    text = re.sub(r'<[^>]+>', '\n', text)
    text = re.sub(r'&[a-z]+;', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def build_huangdaxian():
    """黄大仙灵签 (100 signs) scraped from 51chouqian.com

    HTML structure in div#details_cnt:
    - <h1>黄大仙灵签 第X签：上上 姜公封相</h1>
    - <p>黄大仙灵签 第一签：上上 姜公封相</p>
    - <p>【签词】</p><p>灵签求得第一枝：...</p>
    - <p>【典故】</p><p>周朝开国功臣...</p>
    - <p>〖释义〗</p><p>风水：...</p>
    - <p>〖签解〗</p><p>姜公，姜子牙...</p>
    """
    print("=== Building huangdaxian.json ===")
    results = []
    for i in range(1, 101):
        url = f"https://www.51chouqian.com/huangdaxianlingqian/{i}.html"
        try:
            r = requests.get(url, timeout=15)
            r.encoding = 'utf-8'
            html = r.text
        except Exception as e:
            print(f"  SKIP {i}: {e}")
            results.append({"number": i, "level": "", "poem": "", "interpretation": "", "story": ""})
            continue

        # Extract content from details_cnt div
        cnt_m = re.search(r'id="details_cnt"[^>]*>(.*?)</div>', html, re.DOTALL)
        if not cnt_m:
            print(f"  WARN {i}: no details_cnt div found")
            results.append({"number": i, "level": "", "poem": "", "interpretation": "", "story": ""})
            continue
        content = cnt_m.group(1)

        # Level from <h1> title: "黄大仙灵签 第1签：上上 姜公封相"
        level = ""
        title_m = re.search(r'第\d+签[：:](\S+)\s', html)
        if title_m:
            level = title_m.group(1)

        # Extract title/ancient figure
        title = ""
        title_m2 = re.search(r'第\d+签[：:]\S+\s+(.+?)</h1>', html)
        if title_m2:
            title = title_m2.group(1).strip()

        # Split content by sections: 【签词】【典故】〖释义〗〖签解〗
        # Convert to plain text first
        text = clean_html(content)

        # Extract poem (between 【签词】 and 【典故】 or 〖)
        poem = ""
        pm = re.search(r'【签词】\s*(.*?)(?:【典故】|〖|$)', text, re.DOTALL)
        if pm:
            poem = pm.group(1).strip()

        # Extract story (between 【典故】 and 〖 or end)
        story = ""
        sm = re.search(r'【典故】\s*(.*?)(?:〖|$)', text, re.DOTALL)
        if sm:
            story = sm.group(1).strip()

        # Extract interpretation (〖签解〗 section)
        interpretation = ""
        im = re.search(r'〖签解〗\s*(.*?)(?:流年[：:]|$)', text, re.DOTALL)
        if im:
            interpretation = im.group(1).strip()
        # If no 签解 section, try 释义
        if not interpretation:
            im = re.search(r'〖释义〗\s*(.*?)(?:〖签解〗|$)', text, re.DOTALL)
            if im:
                interpretation = im.group(1).strip()

        results.append({
            "number": i,
            "level": level,
            "poem": poem,
            "interpretation": interpretation,
            "story": f"【{title}】\n{story}" if title and story else (story or title or ""),
        })
        if i % 25 == 0:
            print(f"  {i}/100")
        time.sleep(0.3)

    path = os.path.join(OUTDIR, "huangdaxian.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  -> {len(results)} signs saved")


if __name__ == '__main__':
    import sys
    targets = sys.argv[1:] if len(sys.argv) > 1 else ['guanyin', 'zhuge', 'huangdaxian']
    if 'guanyin' in targets:
        build_guanyin()
    if 'zhuge' in targets:
        build_zhuge()
    if 'huangdaxian' in targets:
        build_huangdaxian()
    # Cleanup
    for f in ['zhuge_raw.json', 'debug.txt']:
        p = os.path.join(OUTDIR, f)
        if os.path.exists(p):
            os.remove(p)
    print("\nDone!")
