"""Lesson: rsync — 把資料夾 A 同步到 B 的七個情境.

Content only. The engine (src/build.py + src/overlay.py) renders it; the
environment is built by the sibling setup.sh (source A, dest B, scratch C).
See src/lesson.py for the S()/R()/CLR() contract and the token role colours.
"""
from lesson import S, R, CLR

SLUG = "rsync"
TITLE = "rsync 教學 · 七個同步情境"

SCRIPT = [
    CLR(key="rsync · 把 A 同步到 B"),
    S("先來認識這兩個資料夾，A 是來源，B 是目標。"),
    S("我們先看看來源 A 裡面有什麼。"),
    R("tree -a A"),
    S("有原始碼、文件，還有一個比較大的檔案。"),
    S("再看看目標 B。"),
    R("tree B"),
    S("它只有一份舊的 README，和一個多餘的 obsolete 檔案。"),

    CLR(key="先預覽：-n 只看不動手", hero="rsync -a -v -n A/ B/", toks=[
        ("-a", "封存模式，保留權限與目錄結構", "ord"),
        ("-v", "顯示傳輸細節", "ord"),
        ("-n", "dry-run：只列出計畫，不動檔案", "star"),
        ("A/ B/", "複製 A 的內容到 B", "path")]),
    S("同步之前，先養成預覽的好習慣。"),
    S("先用 -a 封存、加上 -v 顯示細節，再放上關鍵的 -n，把來源 A 同步到 B。"),
    R("rsync -a -v -n A/ B/"),
    S("你看，它只列出了計畫，並用 DRY RUN 標示，完全不會動到檔案。"),

    CLR(key="-a -v 標準同步", hero="rsync -a -v A/ B/", toks=[
        ("-a", "封存模式：保留權限、時間、目錄結構", "star"),
        ("-v", "顯示傳輸細節", "ord"),
        ("A/ B/", "結尾斜線＝複製內容，非資料夾", "path")]),
    S("確認沒問題，我們就正式同步。"),
    S("這次用 -a 封存模式、搭配 -v 顯示細節，把 A 的內容複製到 B。"),
    R("rsync -a -v A/ B/"),
    S("所有檔案，都成功複製過去了。"),
    R("tree B"),
    S("現在 B 的內容，跟來源 A 一模一樣。"),

    CLR(key="鏡像同步：--delete 讓 B 跟 A 一致",
        hero="rsync -a -v --delete A/ B/", toks=[
        ("-a", "封存模式，保留權限/時間", "ord"),
        ("-v", "顯示傳輸細節", "ord"),
        ("--delete", "鏡像：刪除 B 裡 A 沒有的檔案", "star"),
        ("A/ B/", "複製 A 的內容到 B", "path")]),
    S("那如果想讓 B 變成 A 的完整鏡像呢？"),
    S("一樣用 -a 封存、-v 顯示細節，再加上 --delete，讓 B 完全對齊 A。"),
    R("rsync -a -v --delete A/ B/"),
    S("注意這一行，多餘的 obsolete 檔案被刪掉了，這個選項要小心使用。"),

    CLR(key="用 --exclude 跳過不要的檔",
        hero="rsync -a -v --exclude='*.log' --exclude='.cache/' A/ C/", toks=[
        ("-a", "封存模式，保留結構", "ord"),
        ("-v", "顯示細節", "ord"),
        ("--exclude", "排除符合樣式的檔案，可重複（*.log、.cache/）", "star"),
        ("A/ C/", "這次目標是新資料夾 C", "path")]),
    S("有些檔案我們並不想同步，例如快取和日誌。"),
    S("用 -a 封存、-v 顯示細節，再用 --exclude 排除掉 log 跟 cache，同步到新的 C。"),
    R("rsync -a -v --exclude='*.log' --exclude='.cache/' A/ C/"),
    S("可以看到，cache 目錄和所有的 log 檔，都被跳過了。"),
    R("tree -a C"),
    S("C 裡面乾乾淨淨，只留下我們真正想要的檔案。"),

    CLR(key="-z 壓縮 + 進度顯示", hero="rsync -a -z --info=progress2 A/ C/",
        toks=[
        ("-a", "封存模式", "ord"),
        ("-z", "壓縮資料，節省傳輸頻寬", "star"),
        ("--info=progress2", "顯示整體傳輸進度", "ord"),
        ("A/ C/", "同步到資料夾 C", "path")]),
    S("傳輸大檔，或透過網路同步時，速度就很重要。"),
    S("我先把這個大檔，改得更大一些。"),
    R("head -c 12000000 /dev/urandom > A/data/archive.bin"),
    S("這次用 -a 封存、加上 -z 壓縮，再用 info=progress2 顯示進度，同步到 C。"),
    R("rsync -a -z --info=progress2 A/ C/"),
    S("進度條一路跑到百分之百，大檔也同步完成了。"),

    CLR(key="-i 看懂每行變更", hero="rsync -a -v -i A/ B/", toks=[
        ("-a", "封存模式", "ord"),
        ("-v", "顯示細節", "ord"),
        ("-i", "itemize：每行符號標示變更類型", "star"),
        ("A/ B/", "複製 A 的內容到 B", "path")]),
    S("最後一個技巧，學會看懂 rsync 的輸出。"),
    S("用 -a 封存、-v 顯示細節，最後加上 -i，把每一筆變更都標示出來。"),
    R("rsync -a -v -i A/ B/"),
    S("開頭的符號，會告訴你檔案是新增、更新，還是只有屬性改變。"),
    S("掌握這幾招，你就能應付大多數的 rsync 情境了。"),
]
