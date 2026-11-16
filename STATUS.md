# 待老師確認事項

1. **推導答案/解析共 64 則**(App 內標「推導」):試題演練全部、各 類題、Unit 2 綜合測驗類題。書上無印答案,是我自行推導,請抽查。
2. **掃描被截斷的段落**:p14–18、32、34 右緣文字被相機角度切掉,我依上下文還原(含 planarian 段落),請對照原書。
3. **年份疑似印刷錯誤**:書中某解析印 (2000→2005),我寫成 2025。
4. **Unit 2 閱讀 類題 Q6 (Doc McStuffins)**:選項 D 有歧義,已在題目中註記。
5. **clarify** 不在書中單字表,字典中以 ECDICT 補上。
6. **音標**:原書單字表未轉錄音標。
7. 有 20 個 `'s` 形式無獨立釋義,App 以去掉 `'s` 查詢。

## 翻譯(新增,來自另一本「翻譯／寫作」書,p.2–7)
8. **新題型 `trans`**:學生在紙上作答,App 不放輸入框、不自動批改。每題只有一顆「看參考答案」按鈕,按下顯示參考答案(答案可能不只一種)與書上的「替換詞」;老師可用一個總開關決定是否顯示翻譯答案(關閉時答案按鈕全部隱藏,上課時不讓學生偷看);開關狀態要記住上次的設定(存 localStorage)。已做在新版 app.js / index.html / style.css / sw.js(Project 內 claude/ 底下,以北模隨身讀的程式為基礎改寫);開關在每個翻譯單元頂端與「設定」裡,狀態存在 localStorage。新版 CACHE 為 workbook-reader-v2,部署前需用 `build_data.py` 重新產生 data.js / dictionary.js,並確認原書頁面圖檔命名(assets/page-6.jpg 或 page-06.jpg,兩種都會嘗試)。
9. **試題演練各 8 題(翻譯一、二共 16 題)**書上沒有印答案,參考答案為 Claude 推導(標「推導」),請老師審閱。其中 翻譯二 試題演練 8「Not sure whether he had passed…」時態、試題演練 3 的分詞構句寫法可有多種,參考答案僅供一種。
10. 歷屆範例 5(翻譯二 Q5)中文「許多學生而言」原書掃描左緣被切,我補為「對許多學生而言」。
11. 翻譯一 Q5 的「help + (人) + (to) VR」是掃描上的紅字補充,已收為「補充」。學生在書上的手寫作答與紅筆批改沒有收錄。
12. 翻譯 section 沒有 `@pages`(新書沒有 assets/page-*.jpg),原書頁面核對功能對這兩個 section 不適用。
13. 尚未收:翻譯(三)–(八)、翻譯複習(一)(二),以及寫作(一)–(八)。

## 書本架構(2026-11-11)
14. 首頁為四本書入口:**Grand Slam**(大滿貫,目前 Unit 1–3 與翻譯一、二)、**Cloze Power-Up**(克漏字開外掛)、**Beat the GSAT**(戰勝學測)、**Level 3–5**。書名已改為只顯示英文(2026-11-11)。Cloze Power-Up、Beat the GSAT 尚無內容,App 顯示「內容準備中」。書本設定在 `tools/build_data.py` 的 `BOOKS` / `UNITS`(每個 unit 有 `book` 欄位)。
15. 翻譯(一)(二)原本來自另一本「翻譯／寫作」書,目前暫放在「Grand Slam」底下,請確認要不要移到別本。
16. 書名英文副標(Grand Slam、Cloze Power-Up、Beat the GSAT、Vocabulary Level 3–5)為暫訂,可在 `BOOKS` 修改。

## Level 3–5(2026-11-11,來自 Vocaboo)
17. 題目與答案由 `tools/import_vocaboo.py` 從 Vocaboo repo(shuanmaker-web/vocab-app 的 `data/questions.json`)匯入,產生 `material/l35-01.txt`–`l35-75.txt`:Unit 1–75,每單元 20 題(文意字彙 1–5、選擇題 6–10、配合題 11–20),共 1,500 題。Vocaboo 更新後重跑 importer 與 build 即可;不要手改 l35-*.txt。
18. 答案與中文詞義在 Vocaboo 已與教材官方解答逐題核對,所以沒有「推導」標記。解析只有「詞義」(原形、詞性、中文)與「原文」(填入答案的完整句子),書上若有更詳細的解析尚未收錄。
19. 題目文字是照片轉錄。Vocaboo 的 CHECKLIST 標記 U19、29、33、35、44、45、55–58 可能有轉錄誤差,這些單元的導讀已註明請抽查。
20. dictionary.js 已用 ECDICT 重新產生(原有字義完全不變),新增 Level 3–5 題目用到的字;臺東、the Wangs 等專有名詞放在 CONTEXT。

## Cloze Power-Up Unit 41–44「Energy」(2026-11-12,來自老師上傳的 PDF 掃描)
21. 題目文字由老師上傳的 PDF(`UNIT 41/42/43/44 — Energy`)逐題轉錄為 `material/cloze-41.txt`–`cloze-44.txt`,每單元固定結構:一、綜合測驗(1–10,選擇題,兩篇各 5 格);二、文意選填(11–20,A–J 選項);三、篇章結構(21–24,A–E 選項),共 96 題。
22. **答案已與老師提供的解答逐字核對、全部相符**(老師給的格式:`41: CABDA DBCAC FDBIAJGCHE BAEC` 這類 24 字母一串,對應 Q1–24),不是 Claude 推導的答案。
23. 但每題的「解析」說明文字是 Claude 另外撰寫的(PDF 本身沒有印解析),已統一標示「推導」,請老師抽查解析內容是否恰當;答案本身不需要再核對。
24. 暫時歸在 **Cloze Power-Up**(克漏字開外掛)這本書底下,因為三個子題型(綜合測驗、文意選填、篇章結構)都是克漏字類型的題目;如果老師覺得應該放在別本,可以再移動(只需調整 `tools/build_data.py` 的 `UNITS`)。
25. Pavegen、Fosen Vind、GoSun、Bloom Energy、electrocytes、elephantnose 等新專有名詞已加進 `CONTEXT` 字典;dictionary.js 已用 ECDICT 重新產生。CACHE 版本已更新為 `workbook-reader-v6`。

## Cloze Power-Up Unit 45–48「Technology」(2026-11-12,來自老師上傳的 PDF 掃描)
26. 題目文字由老師上傳的 PDF(`UNIT 45/46/47/48 — Technology`)逐題轉錄為 `material/cloze-45.txt`–`cloze-48.txt`,結構與 Unit 41–44 相同:一、綜合測驗(1–10,選擇題,兩篇各 5 格);二、文意選填(11–20,A–J 選項);三、篇章結構(21–24,A–E 選項),共 96 題。主題包括 SlothBot、人臉辨識、自動駕駛列車(Unit 45)、垂直農場、觸控螢幕、冷氣機發明、iFetch 自動丟球機(Unit 46)、5G、AI 魔術表演、蝴蝶鍵盤、防水科技(Unit 47)、嬰兒智慧襪、《駭客任務》劇情、腦震盪感測牙套、智慧義大利麵機(Unit 48)。
27. **答案已與老師提供的解答逐字核對、全部相符**(老師給的格式:`45: BDABD CCBCD EAFGB CIHDJ DCAB` 這類 24 字母一串,對應 Q1–24),不是 Claude 推導的答案。
28. 但每題的「解析」說明文字是 Claude 另外撰寫的(PDF 本身沒有印解析),已統一標示「推導」,請老師抽查解析內容是否恰當;答案本身不需要再核對。
29. 暫時歸在 **Cloze Power-Up**(克漏字開外掛)這本書底下,和 Unit 41–44 並列;如果老師覺得應該放在別本,可以再移動(只需調整 `tools/build_data.py` 的 `UNITS`)。
30. Dong Nguyen(Flappy Bird 開發者)、河內、Faby、JR(Japan Railways)、Siemens、漢堡、復興號、北京、Willis Carrier、iFetch、Neo、The Matrix 等新專有名詞已加進 `CONTEXT` 字典;dictionary.js 已用 ECDICT 重新產生。CACHE 版本已更新為 `workbook-reader-v7`。

## Grand Slam Unit 3–4 + 大滿貫特訓(一)(2026-11-17,來自老師上傳的 PDF「Cloze and Reading Units 3 and 4」,原書頁碼 35–63)
31. 這份 PDF 是打字版(非掃描),文字直接取自 PDF,不需要還原截斷的段落。Unit 3 原本只有開頭一頁單字表,現已補齊:單字、片語(附音標)、試題演練、綜合測驗(代名詞)、篇章結構(重複/類似的字詞或文意)、閱讀測驗(作者態度題)。Unit 4:單字、片語(附音標)、試題演練、文意選填(醫療與健康)、篇章結構(段落文意連貫性與一致性)、閱讀測驗(字詞推論一)。另新增「大滿貫特訓(一)」詞彙題 10 題(單元按鈕顯示為「特訓(一)」)。
32. **推導答案/解析新增 74 則**(App 內標「推導」):Unit 3、4 試題演練各 14 題;綜合測驗類題 10 題;Unit 4 文意選填類題 10 題;兩個單元的篇章結構類題各 4 題、閱讀類題各 4 題;特訓(一)10 題。PDF 沒有印這些題目的解答,請抽查。歷屆試題範例(共 29 題)照抄 PDF 上的解析。
33. 需要老師特別確認的推導:Unit 3 閱讀類題 Q3(sorbet 多選)我給 AC,其中 (C)「加入異國水果始於歐洲」需要推論;Unit 4 文意選填類題第 7、9 格 furthermore / though 兩個副詞的位置,我依「句尾只能放 though」判斷第 9 格為 though、第 7 格為 furthermore;Unit 3 綜合測驗類題第 10 格選 few(「很少有提醒比……更重要」)。
34. 原書頁面核對:這批沒有掃描圖檔,所以 Unit 3、4 與特訓(一)沒有 `@pages`,不顯示「原書頁面核對」按鈕。
35. 單字表首次加入**音標**(material 語法:`= word` 下一行寫 `[ˈfɔnɪk]`),只有 Unit 3、4 有;Unit 1、2 仍無音標(第 6 項)。
36. 介面調整:(a)移除左側欄「一台 iPad,四本書。選一本書開始上課;單字、題目、解析都在這裡。」三行,以及綠色區塊(首頁、題目、解析、我的單字)裡的中文介紹文字,方便分享螢幕給學生;(b)側欄新增**單元切換列**:`Units` / `Translation` 兩個分頁 + 單元按鈕(1、2、3、4、特訓(一);翻譯(一)、翻譯(二)),側欄只列出目前單元的各節,不用再上下捲動;每個單元、每個分頁都會記住上次看的位置。手機版(側欄隱藏時)同一排按鈕會出現在綠色區塊下方。其他書也適用(Cloze Power-Up 顯示 41–48,Level 3–5 顯示 1–10…71–75)。
37. 翻譯(一)(二)原本是同一個 unit「翻譯」,現在拆成兩個 unit(`tr1`、`tr2`,kind = `trans`),之後加翻譯(三)起只要在 `UNITS` 加一行 kind 為 `trans` 的 unit。section id(`tr-1`、`tr-2`)沒變,學生作答紀錄不受影響。
38. Camino de Santiago、Ka Mate / Kapa o Pango、Louis XIV、Maniq、Jahai、GABA、Popole Misenga、TSMC、Hon Hai 等專有名詞已加進 `CONTEXT`;dictionary.js 已用 ECDICT 重新產生。CACHE 版本已更新為 `workbook-reader-v9`。
39. **合併注意**:Project 裡的 `claude/app.js` / `index.html` / `style.css` 曾有一版(CACHE v8)沒有 push 到 repo,內含「題型分頁(全部／各 group)」、「選項庫固定在畫面下方(bank dock)」、首頁綠色區塊改英文、側欄底部改英文。這次已把那些功能合併進來,再加上 Unit 3–4 與單元切換列;首頁綠色區塊的英文介紹文字也一併拿掉(只留 TUTOR'S BAG 與統計)。合併後的版本 CACHE 為 `workbook-reader-v9`,repo 與 Project 現在一致(repo 尚未 commit)。

## 翻譯（三）（四）、翻譯複習（一）、寫作（一）（二）(2026-11-17,來自老師拍的「翻譯／寫作」書 p.8–15、30–33)
40. 新增翻譯（三）現在完成式、翻譯（四）名詞子句(各:歷屆範例 5 題照抄書上答案與替換詞、試題演練 8 題)、翻譯複習（一）(8 題,每題前後兩句)。翻譯（二）p.5–7 先前已收,這次的照片沒有新內容。
41. **推導答案新增 24 則**:翻譯（三）（四）試題演練各 8 題、翻譯複習（一）8 題,書上沒有印答案,參考答案為 Claude 推導(標「推導」),請審閱。翻譯複習（一）第 8 題中文「為了…，自己出國旅行是很多青少年的夢想」,為避免懸垂的目的片語,參考答案改寫成 many teenagers dream of traveling abroad on their own。
42. **寫作**成為側欄第三個分頁(`Units` / `Translation` / `Writing`),目前有寫作（一）（二):實用句型、歷屆寫作範例(題目 + 書上範文,照抄)、試題演練(只有題目;書上沒有範文,App 顯示「學生在紙上寫作」)。新題型 `write`:範文可有可無,`" ¶ "` 表示分段;範文與翻譯參考答案共用同一個顯示開關。
43. CACHE 版本更新為 `workbook-reader-v10`。
