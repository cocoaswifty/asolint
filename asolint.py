#!/usr/bin/env python3
"""asolint — 用公開 iTunes API 對 App Store 商店頁做「在地化與首屏」健檢。

零依賴（只用標準函式庫），只讀公開資料，不登入、不抓取非公開資料。
輸出可直接寄給開發者的 Markdown 稽核草稿，或 JSON 供後續處理。

用法：
    python asolint.py --app https://apps.apple.com/tw/app/id6443918070 --country tw
    python asolint.py --app 6443918070 --country jp --targets ZH,EN
    python asolint.py --app 6443918070 --json
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://itunes.apple.com/lookup"

# 常見「首屏高價值」語言代碼（iTunes languageCodesISO2A 使用的 2 碼）
DEFAULT_TARGETS = ["ZH", "JA", "KO"]

# 目標市場常見語言 → 顯示名稱
LANG_NAMES = {
    "ZH": "中文（繁/簡）", "JA": "日文", "KO": "韓文", "EN": "英文",
    "ES": "西班牙文", "PT": "葡萄牙文", "FR": "法文", "DE": "德文",
    "IT": "義大利文", "RU": "俄文", "TH": "泰文", "VI": "越南文",
    "ID": "印尼文", "AR": "阿拉伯文", "TR": "土耳其文", "HI": "印地文",
}

COUNTRY_NAMES = {
    "tw": "台灣", "jp": "日本", "kr": "南韓", "us": "美國",
    "hk": "香港", "cn": "中國", "sg": "新加坡",
}


def parse_app_id(value: str) -> str:
    """從 App Store URL 或裸數字取出 app id。"""
    value = value.strip()
    digits = re.search(r"id(\d{6,})", value)
    if digits:
        return digits.group(1)
    if value.isdigit() and len(value) >= 6:
        return value
    raise ValueError(f"無法從 {value!r} 取得 App Store id（需形如 id123456789）")


def fetch_app(app_id: str, country: str = "tw", timeout: int = 20) -> dict:
    """向公開 iTunes Lookup API 取得單一 App 的中繼資料。"""
    query = urllib.parse.urlencode({"id": app_id, "country": country})
    url = f"{API}?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": "asolint/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    results = payload.get("results") or []
    if not results:
        raise ValueError(f"在 {country} 商店找不到 app id {app_id}（或未上架）")
    return results[0]


def _first_lines(text: str, count: int = 3) -> list[str]:
    """取描述在前幾行的非空行，模擬使用者在商店頁看到的第一屏。"""
    lines = [line.strip() for line in (text or "").splitlines()]
    return [line for line in lines if line][:count]


def analyze(app: dict, targets: list[str] | None = None) -> dict:
    """把中繼資料轉成可稽核的發現清單（不含未經證實的成效主張）。"""
    targets = [t.upper() for t in (targets or DEFAULT_TARGETS)]
    langs = set(app.get("languageCodesISO2A") or [])
    iphone_shots = app.get("screenshotUrls") or []
    ipad_shots = app.get("ipadScreenshotUrls") or []
    description = app.get("description") or ""
    rating_count = int(app.get("userRatingCount") or 0)
    rating = app.get("averageUserRating")

    missing = [t for t in targets if t not in langs]

    findings: list[dict] = []

    def add(severity: str, title: str, evidence: str, suggest: str) -> None:
        findings.append({
            "severity": severity, "title": title,
            "evidence": evidence, "suggest": suggest,
        })

    if missing:
        names = "、".join(LANG_NAMES.get(t, t) for t in missing)
        add(
            "high",
            f"缺少 {names} 商店頁語言",
            f"languageCodes 為 {sorted(langs) or '（空）'}；未含 {missing}",
            f"在 App Store Connect 補上 {missing} 的商店頁在地化，"
            "至少翻譯副標題與前 5 行描述，讓首屏秒懂價值。",
        )
    else:
        add(
            "info",
            f"已涵蓋目標語言 {targets}",
            f"languageCodes 含 {[t for t in targets if t in langs]}",
            "可進一步檢查翻譯品質與關鍵字是否在地化，而非直譯。",
        )

    if len(iphone_shots) < 4:
        add(
            "high" if len(iphone_shots) < 3 else "medium",
            f"iPhone 截圖僅 {len(iphone_shots)} 張",
            f"screenshotUrls 共 {len(iphone_shots)} 張",
            "前 3 張截圖是主要轉換素材；建議各放一句主張與一個畫面，"
            "用 Product Page Optimization 對圖像做 A/B 測試。",
        )
    if not ipad_shots:
        add(
            "low",
            "沒有 iPad 截圖",
            "ipadScreenshotUrls 為空",
            "若 App 支援 iPad，補上 iPad 截圖能覆蓋平板使用者。",
        )

    first = _first_lines(description, 3)
    if first:
        add(
            "medium",
            "商店頁描述首屏（前 3 行）內容",
            "／".join(first)[:240],
            "把「使用者能得到什麼」放在第一行；功能清單往後移。"
            "這是文案假說，正式成效需以變更前後的數據佐證。",
        )

    if rating_count < 50:
        add(
            "medium",
            f"評分數偏少（{rating_count} 則）",
            f"userRatingCount={rating_count}, averageUserRating={rating:.2f}"
            if rating else f"userRatingCount={rating_count}",
            "新品或低曝光時，可請滿意的使用者評分（需遵守 Apple 規範，"
            "不得以獎勵換評分或造假）。",
        )

    release = app.get("currentVersionReleaseDate") or ""
    if release:
        try:
            released = datetime.fromisoformat(release.replace("Z", "+00:00"))
            days = (datetime.now(timezone.utc) - released).days
            add(
                "info",
                f"最後更新距今 {days} 天",
                f"currentVersionReleaseDate={release}",
                "持續更新是正面訊號；更新時可在版本說明簡短說明改進。",
            )
        except ValueError:
            pass

    weights = {"high": 22, "medium": 10, "low": 4, "info": 0}
    score = max(0, 100 - sum(weights[f["severity"]] for f in findings))

    return {
        "app_id": str(app.get("trackId", "")),
        "name": app.get("trackName", ""),
        "seller": app.get("sellerName", ""),
        "genre": app.get("primaryGenreName", ""),
        "country": app.get("country", ""),
        "url": app.get("trackViewUrl", ""),
        "rating": round(rating, 2) if rating else None,
        "rating_count": rating_count,
        "languages": sorted(langs),
        "targets": targets,
        "missing_targets": missing,
        "screenshots": len(iphone_shots),
        "ipad_screenshots": len(ipad_shots),
        "score": score,
        "findings": findings,
        "analyzed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def render_markdown(result: dict) -> str:
    """輸出可直接寄給開發者的稽核草稿；未證實處一律標為假說。"""
    country = result.get("country", "").lower()
    market = COUNTRY_NAMES.get(country, country.upper() or "此市場")
    lines = [
        f"# App Store 商店頁健檢：{result['name']}",
        "",
        f"- 市場：{market}（{country}）",
        f"- 賣家：{result['seller']}｜類別：{result['genre']}",
        f"- 評分：{result['rating']}（{result['rating_count']} 則）",
        f"- 商店頁語言：{', '.join(result['languages']) or '（無）'}",
        f"- 健檢分數：**{result['score']}/100**（滿分 100，僅為啟發式指標）",
        f"- 產生時間（UTC）：{result['analyzed_utc']}",
        "",
        "> 本報告只根據公開 iTunes API 的中繼資料，"
        "不含任何轉換率或排名的實測數據；下列所有改善皆為**待驗證的假說**。",
        "",
        "## 依嚴重度排序的發現",
        "",
    ]
    order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    for finding in sorted(result["findings"], key=lambda f: order[f["severity"]]):
        tag = {"high": "🔴 高", "medium": "🟠 中", "low": "🟡 低", "info": "⚪ 參考"}[finding["severity"]]
        lines += [
            f"### {tag}｜{finding['title']}",
            f"- 證據：{finding['evidence']}",
            f"- 建議：{finding['suggest']}",
            "",
        ]
    lines += [
        "## 可進一步（需人工確認）",
        "- [ ] 實際檢視前 3 張截圖的文案與構圖",
        "- [ ] 對照 2–3 個同類競品的商店頁",
        "- [ ] 確認副標題與關鍵字是否在地化，而非直譯",
        "",
        "---",
        "由 asolint（開源工具）產生。若要『文案重寫 + 截圖敘事 + 同類對照』的完整交付，"
        "見專案內 `docs/OFFER.md`。",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="App Store 商店頁在地化與首屏健檢（公開資料）")
    parser.add_argument("--app", required=True, help="App Store URL 或 app id")
    parser.add_argument("--country", default="tw", help="商店國家碼，例如 tw/jp/us")
    parser.add_argument("--targets", default=",".join(DEFAULT_TARGETS),
                        help="目標語言代碼，逗號分隔，例如 ZH,JA,KO")
    parser.add_argument("--json", action="store_true", help="以 JSON 輸出")
    args = parser.parse_args()

    try:
        app_id = parse_app_id(args.app)
        app = fetch_app(app_id, country=args.country)
        app["country"] = app.get("country") or args.country
        targets = [t.strip() for t in args.targets.split(",") if t.strip()]
        result = analyze(app, targets)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
