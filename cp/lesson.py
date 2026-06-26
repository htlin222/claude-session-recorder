"""cp 教學 · 在命令列複製檔案與目錄（macOS BSD cp）— 這個 clip 的內容檔。

每個情境教 cp 的一個旗標，從最基本的 `cp 來源 目的`，一路走到遞迴、保留屬性、
不覆蓋、囉嗦輸出、合併旗標與封存模式。所有指令都跑在 lab/ 子資料夾裡，輸出乾淨可
重現。平台註記：這裡渲染在 macOS，內建的 cp/ls/stat/cat 是 BSD 變體，輸出與 Linux
的 GNU 版略有不同；為了和 Linux 對齊，全程改用 gcp/gls/gstat/gcat（GNU coreutils），
在 Linux 上就是直接打 cp/ls/stat/cat。
"""
from clipkit import S, R, CLR

SLUG = "cp"
TITLE = "cp 教學 · 在命令列複製檔案與目錄（macOS BSD cp）"

SCRIPT = [
    CLR(key="cp · 在命令列複製檔案與目錄"),
    S("不管是備份重要檔案、整理專案，還是先留一份草稿再來改，我們每天都在命令列上複製東西。"),
    S("最基本、也最常用的工具，就是 cp，也就是英文 copy 的縮寫。"),
    S("不過要特別注意，macOS 內建的 cp 是 BSD 版本，跟 Linux 上的 GNU cp 在一些細節上並不完全一樣。"),
    S("為了讓畫面上的輸出和 Linux 使用者看到的一致，這個教學一律改用 gcp，也就是 GNU coreutils 提供的版本。"),
    S("在 Linux 上你直接打 cp 就是這個行為，在 macOS 上先用 brew 裝好 coreutils，就會有 gcp 可以用。"),
    S("同樣的道理，這次列檔案我們用 gls，看時間戳用 gstat，看內容則用 gcat，都是為了和 Linux 對齊。"),
    S("接下來就從看一眼範例檔案開始，一步一步把 cp 的各個旗標走過一遍。"),

    CLR(key="先進到範例資料夾，看看裡面有哪些檔案", hero="gls -l", toks=[
        ("gls", "GNU 版的 ls", "path"),
        ("-l", "用長格式顯示細節", "star")]),
    S("動手之前，先進到已經幫你準備好的範例資料夾 lab 裡面。"),
    R("cd lab"),
    S("接著用 gls 搭配 -l 旗標，以長格式列出，把權限、大小和修改時間一併秀出來。"),
    R("gls -l"),
    S("裡面有幾個文字檔，一個 docs 子目錄，還有一個刻意設成 2020 年的 stamped 檔，以及一個空的 backup 目錄。"),

    CLR(key="最基本的用法：cp 來源 目的", hero="gcp a.txt copy.txt", toks=[
        ("gcp", "複製檔案", "path"),
        ("a.txt", "第一個參數是來源", "path"),
        ("copy.txt", "第二個參數是目的", "star")]),
    S("先從最基本的形式開始，cp 後面接兩個參數，前面是來源，後面是目的。"),
    S("這裡我們把 a.txt 複製一份，新檔案命名為 copy.txt。"),
    R("gcp a.txt copy.txt"),
    S("指令安靜地做完，沒有任何輸出，原本的 a.txt 還在，旁邊多了一份一模一樣的副本。"),
    S("這就是 cp 最核心的動作，把一份資料完整地複製成兩份。"),

    CLR(key="目的地是目錄：結尾加斜線複製進去", hero="gcp report.txt backup/", toks=[
        ("gcp", "複製", "path"),
        ("report.txt", "來源檔", "path"),
        ("backup/", "目的地是一個目錄", "star")]),
    S("如果目的地是一個已經存在的目錄，cp 會把檔案複製到那個目錄裡面。"),
    S("我們把目的地寫成 backup/，結尾的那一條斜線清楚表示這是一個目錄。"),
    R("gcp report.txt backup/"),
    S("report.txt 被原樣放進了 backup 目錄，檔名維持不變。"),

    CLR(key="一次把多個檔案複製進同一個目錄", hero="gcp a.txt b.txt backup/", toks=[
        ("a.txt", "第一個來源", "path"),
        ("b.txt", "第二個來源", "path"),
        ("backup/", "最後一個參數是目的目錄", "star")]),
    S("cp 也可以一次複製很多個檔案，規則是把目錄放在最後一個參數。"),
    S("這次我們同時把 a.txt 和 b.txt 兩個檔案，一起送進 backup/ 目錄。"),
    R("gcp a.txt b.txt backup/"),
    S("兩個檔案一次就位，這種多來源、單一目錄的寫法在日常非常常用到。"),

    CLR(key="-r：遞迴複製整個目錄", hero="gcp -r docs docs-backup", toks=[
        ("gcp", "複製", "path"),
        ("-r", "遞迴複製目錄與內容", "star"),
        ("docs", "來源目錄", "path"),
        ("docs-backup", "新的目的目錄", "path")]),
    S("前面複製的都是單一檔案，那如果想複製的是整個目錄呢？"),
    S("直接拿 cp 去複製一個目錄會被拒絕，必須加上 -r 這個旗標，代表遞迴處理。"),
    S("加了 -r，cp 就會連同目錄底下的所有子檔案和子目錄一起複製過去。"),
    R("gcp -r docs docs-backup"),
    S("整個 docs 目錄被完整複製成 docs-backup，裡面的內容一個都沒漏掉。"),

    CLR(key="-p：保留權限、擁有者與時間戳", hero="gcp -p stamped.txt kept.txt", toks=[
        ("gcp", "複製", "path"),
        ("-p", "保留原檔的屬性", "star"),
        ("stamped.txt", "來源檔", "path"),
        ("kept.txt", "目的檔", "path")]),
    S("預設情況下，複製出來的新檔案，修改時間會被換成現在這一刻。"),
    S("如果你想保留原本的權限、擁有者和時間戳，就加上 -p 這個旗標。"),
    S("我們的 stamped.txt 被刻意設成 2020 年，正好拿來驗證 -p 有沒有真的生效。"),
    R("gcp -p stamped.txt kept.txt"),
    S("新的 kept.txt 連時間戳都和來源一樣停在 2020 年，屬性被完整保留了下來。"),

    CLR(key="-n：不覆蓋已經存在的檔案", hero="gcp -n a.txt copy.txt", toks=[
        ("gcp", "複製", "path"),
        ("-n", "遇到既有檔案就不覆蓋", "star"),
        ("a.txt", "來源", "path"),
        ("copy.txt", "已存在的目的檔", "path")]),
    S("複製時如果目的檔已經存在，預設會直接覆蓋掉它，這有時候相當危險。"),
    S("加上 -n 這個旗標，意思是 no clobber，遇到已經存在的檔案就安靜地跳過。"),
    S("還記得前面建立的 copy.txt 嗎，我們故意再拿 a.txt 去蓋它看看會怎樣。"),
    R("gcp -n a.txt copy.txt"),
    S("指令什麼都沒說，因為它判斷 copy.txt 已經存在，於是就直接略過了。"),
    S("用 gcat 把 copy.txt 印出來，內容還是原本那一份，證明它確實沒有被覆蓋。"),
    R("gcat copy.txt"),
    S("保護既有檔案不被蓋掉，正是 -n 最實用的地方。"),

    CLR(key="-v：印出每一步複製動作", hero="gcp -v notes.txt copied.txt", toks=[
        ("gcp", "複製", "path"),
        ("-v", "verbose，逐步回報", "star"),
        ("notes.txt", "來源", "path"),
        ("copied.txt", "目的", "path")]),
    S("前面幾個指令做完都靜悄悄的，有時候我們會想知道它到底做了什麼。"),
    S("加上 -v 這個旗標，也就是 verbose，cp 會把每一個複製動作都印出來。"),
    R("gcp -v notes.txt copied.txt"),
    S("畫面上出現一行箭頭，清楚標示 notes.txt 被複製成了 copied.txt。"),
    S("想在複製大量檔案時逐一確認每一步，這個旗標就特別好用。"),

    CLR(key="短旗標可以合併：-rv", hero="gcp -rv docs docs-v", toks=[
        ("gcp", "複製", "path"),
        ("-rv", "把 -r 和 -v 併在一起", "star"),
        ("docs", "來源目錄", "path"),
        ("docs-v", "目的目錄", "path")]),
    S("短旗標其實可以黏在一起寫，不必一個一個分開打。"),
    S("把遞迴的 r 和囉嗦的 v 合併成 -rv，就同時擁有兩個旗標的效果。"),
    R("gcp -rv docs docs-v"),
    S("整個目錄被遞迴複製，而且每一個檔案的複製過程都即時印了出來。"),
    S("這種把短旗標黏在一起的寫法，在各種 Unix 指令裡都很常見。"),

    CLR(key="-a：封存模式，完整保留一切", hero="gcp -a docs archive", toks=[
        ("gcp", "複製", "path"),
        ("-a", "封存模式：遞迴又保留全部屬性", "path"),
        ("docs", "來源目錄", "path"),
        ("archive", "目的目錄", "path")]),
    S("如果要做一份忠實的備份，最方便的就是封存模式。"),
    S("最後介紹的這個封存模式，會遞迴複製，又完整保留權限與時間戳等所有屬性。"),
    R("gcp -a docs archive"),
    S("封存完成後，新目錄裡的內容連同每個檔案的時間戳，都和原本的來源一模一樣。"),

    CLR(key="用 tree 檢視最後的複製成果", hero="tree -L 1", toks=[
        ("tree", "以樹狀圖顯示目錄", "path"),
        ("-L", "限制顯示的層數", "star"),
        ("1", "只看最上面一層", "path")]),
    S("操作了這麼多次，最後用 tree 把整個資料夾畫成一張樹狀圖來收尾。"),
    S("加上 -L 1，只展開最上面一層，畫面才不會被一堆子目錄塞滿。"),
    R("tree -L 1"),
    S("剛剛複製出來的那些檔案和目錄全都列在這裡，每一個旗標的成果一目了然。"),
    S("從最基本的兩個參數，到 -r、-p、-n、-v 和 -a，這些就是日常用 cp 複製檔案最核心的幾招。"),
]
