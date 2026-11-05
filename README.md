# asolint — App Store 商店頁「在地化 + 首屏」健檢 CLI

用**公開**的 iTunes Lookup API，對任何 App Store 商店頁做秒級健檢：找出缺少的目標語言、
截圖數量、描述首屏、評分基數與更新節奏，輸出可寄給開發者的 Markdown 稽核草稿。

- 零依賴（只用 Python 標準函式庫），不登入、不抓非公開資料、不呼叫第三方付費 API。
- 所有改善建議都標為**待驗證假說**，不聲稱任何轉換率或排名成效。

## 安裝／執行

```bash
# 直接用，不需安裝
python3 asolint.py --app https://apps.apple.com/tw/app/id6443918070 --country tw

# 指定目標語言（預設 ZH,JA,KO）
python3 asolint.py --app 6443918070 --country jp --targets ZH,EN

# JSON 輸出，方便接自動化
python3 asolint.py --app 6443918070 --json
```

## 範例輸出

```
# App Store 商店頁健檢：Habit Tracker - HabitKit
- 健檢分數：54/100（僅為啟發式指標）

### 🔴 高｜缺少 中文（繁/簡） 商店頁語言
- 證據：languageCodes ... 未含 ['ZH']
- 建議：補上 ZH 商店頁在地化，至少翻譯副標題與前 5 行描述 ...
```

## 測試

```bash
python3 -m unittest test_asolint -v   # 離線，使用 fixture
```

## 它不能做什麼

- 看不到轉換率、下載數或關鍵字排名（那些只有開發者後台有）。
- 不會自動修改你的商店頁，也不會代替你登入 App Store Connect。
- 分數是啟發式指標，不是 Apple 官方或市場平均值。

## 需要「文案重寫 + 截圖敘事 + 同類對照」？

那屬於人工交付，見專案 `docs/OFFER.md`（固定範圍服務）。

授權：MIT。
