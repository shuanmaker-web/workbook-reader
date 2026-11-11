# Workbook 隨身讀

學測英文 Workbook 的靜態 PWA(仿「北模隨身讀」):點英文單字看中文、我的單字、解析模式、答案揭曉、深色模式、字級、離線。
翻譯單元(翻譯一、二)學生在紙上作答;App 只提供「看參考答案」按鈕,老師可用開關關閉,設定會記住。

## 檔案
- `index.html`、`app.js`、`style.css`、`sw.js`、`manifest.webmanifest`:App 本體(純 vanilla JS,無 build step)。
- `material/*.txt`:題目與單字的文字 DSL(語法見 `tools/build_data.py` 開頭說明)。
- `tools/build_data.py`:讀 `material/*.txt` 產生 `data.js`(window.EXAM)與 `dictionary.js`(window.DICTIONARY)。
- `STATUS.md`:待老師確認事項。

## Level 3–5(來自 Vocaboo)
```bash
python3 tools/import_vocaboo.py /path/to/vocab-app/data/questions.json   # 產生 material/l35-*.txt
```

## 重新產生資料
```bash
python3 tools/build_data.py /path/to/ecdict.csv   # 需要 pip install opencc-python-reimplemented
```
字典優先序:書中單字釋義 > ECDICT(MIT,以 opencc s2tw 轉繁體)> 變化形回到原形。
改內容請改 `material/`,不要直接改 `data.js`。

## 本機測試
```bash
python3 -m http.server 8801   # 開 http://localhost:8801
```

## 改版
同步更新 `sw.js` 與 `app.js` 的 `CACHE` 版本字串(目前 `workbook-reader-v4`)。
localStorage key 為 `workbook-reader-v1`(不要改,以免學生紀錄消失)。

## 注意
- 首頁有四本書:大滿貫、克漏字開外掛、戰勝學測、Level 3–5;書本設定在 `tools/build_data.py` 的 `BOOKS` / `UNITS`。
- 沒有 ECDICT csv 時,`build_data.py` 只重建 `data.js`,不會覆蓋 `dictionary.js`。
- 原書頁面掃描(`assets/page-*.jpg`)已列入 `.gitignore`,不要上傳;公開部署前請確認授權。
- 書上沒有印答案的題目,答案與解析由 Claude 推導並標「推導」,請老師審閱後再給學生使用。
