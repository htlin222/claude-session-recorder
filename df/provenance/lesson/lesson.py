"""Lesson: df — 在命令列查看磁碟空間還剩多少 (GNU gdf).

Tool-agnostic engine; only this file + setup.sh are df-specific. Each scene
dissects one `gdf [flag] [path]` invocation. PLATFORM NOTE: this renders on
macOS, where the built-in `df` is the BSD variant (default 512-byte blocks,
different columns, no -T). To match what a Linux learner sees, EVERY command
uses GNU `gdf` (Homebrew coreutils); on Linux the same command is just `df`.
The explain sentence right before each R() names the scene's flag VERBATIM so
the panel reveal lands in typing-sync.
"""
from clipkit import S, R, CLR

SLUG = "df"
TITLE = "df 教學 · 在命令列查看磁碟空間還剩多少"

SCRIPT = [
    CLR(key="df · 在命令列查看磁碟空間還剩多少"),
    S("磁碟到底還剩多少空間，是每個用終端機的人遲早都要回答的問題。"),
    S("df 這個指令就是用來回報各個檔案系統的磁碟用量，名字來自 disk free。"),
    S("在 macOS 上，內建的 df 是 BSD 版本，預設用 512-byte 區塊，輸出欄位也和 Linux 不太一樣。"),
    S("為了和 Linux 看到的結果一致，我們全程改用 GNU 版的 gdf；在 Linux 上，這支指令的名字就是不帶 g 的 df。"),
    S("接下來我們就從最樸素的一行 gdf 開始，一個旗標一個旗標把磁碟空間看清楚。"),

    CLR(key="gdf：列出每個檔案系統，預設以 1K 區塊計數", hero="gdf", toks=[
        ("gdf", "disk free：回報各檔案系統的磁碟用量", "star")]),
    S("先不帶任何旗標，直接執行 gdf 看看最樸素的輸出。"),
    S("GNU 版的 gdf 預設用 1K 區塊，也就是每個數字的單位都是 1024 byte。"),
    S("欄位依序是裝置、總大小、已用、可用、使用率，最右邊則是掛載點。"),
    R("gdf"),
    S("一眼就能看出每顆磁碟塞了多滿，以及它接在檔案系統的哪個位置。"),

    CLR(key="-h：人類可讀，用 K/M/G 並以 1024 進位", hero="gdf -h", toks=[
        ("gdf", "GNU df", "path"),
        ("-h", "human-readable：自動換算成帶單位的格式", "star")]),
    S("一長串以 1K 為單位的數字，其實並不好讀。"),
    S("加上 -h 旗標，gdf 會自動把大小換算成帶 K、M、G 單位的人類可讀格式。"),
    S("這裡的 -h 採用 1024 進位，所以 G 指的是 2 的 30 次方 byte。"),
    R("gdf -h"),
    S("同樣的資料瞬間清爽很多，這也是日常最常用的一種形式。"),

    CLR(key="-H：改用 1000 進位的 SI 單位", hero="gdf -H", toks=[
        ("gdf", "GNU df", "path"),
        ("-H", "SI：改用 1000 進位換算", "star")]),
    S("硬碟廠商在標示容量時，用的是 1000 進位，而不是 1024。"),
    S("把旗標換成大寫的 -H，gdf 就改用 SI 單位，以 1000 為一級往上換算。"),
    S("差別就在進位的基準：小寫 -h 是每 1024 進一位，大寫 -H 則是每 1000 進一位。"),
    R("gdf -H"),
    S("同一顆磁碟在 -H 底下的 G 數，會比剛剛的 -h 稍微大一些。"),

    CLR(key="-m：所有大小固定用 MB 顯示", hero="gdf -m", toks=[
        ("gdf", "GNU df", "path"),
        ("-m", "固定用 1M 區塊，全部換算成 MB", "star")]),
    S("有時候我們想要一個固定不變、好做比較的單位。"),
    S("-m 旗標讓 gdf 一律用 1M 區塊，把每個大小都換算成 MB 的整數。"),
    R("gdf -m"),
    S("不管磁碟多大都用同一個單位，多顆並排時欄位會對得特別整齊。"),

    CLR(key="-i：改看 inode 用量而非容量", hero="gdf -i", toks=[
        ("gdf", "GNU df", "path"),
        ("-i", "inodes：改看 inode 用量", "star")]),
    S("磁碟空間明明沒滿，檔案卻寫不進去，常常是 inode 用光了。"),
    S("加上 -i 旗標，gdf 就改成回報每個檔案系統的 inode 數量。"),
    S("欄位換成 Inodes、IUsed、IFree、IUse%，數的是檔案個數而不是容量。"),
    R("gdf -i"),
    S("如果某一列的 IUse% 接近百分之百，那就算還有空間也建立不了新檔案。"),

    CLR(key="-T：在輸出裡多印一欄檔案系統型別", hero="gdf -T -h /", toks=[
        ("gdf", "GNU df", "path"),
        ("-T", "print-type：多印一欄檔案系統型別", "star"),
        ("-h", "順便人類可讀", "ord"),
        ("/", "只看根目錄這一個檔案系統", "path")]),
    S("有時我們也想知道某一顆磁碟到底是什麼格式。"),
    S("-T 旗標會在輸出裡多加一欄 Type，這次同時搭配 -h，並只查根目錄 / 這一個檔案系統。"),
    R("gdf -T -h /"),
    S("在 macOS 上會看到 apfs，在 Linux 上則可能是 ext4 或 xfs。"),

    CLR(key="gdf /：只查一個路徑所在的檔案系統", hero="gdf /", toks=[
        ("gdf", "GNU df", "path"),
        ("/", "解析這個路徑所在的檔案系統", "path")]),
    S("前面都是一次列出全部，但通常我們只關心某一個位置。"),
    S("在 gdf 後面直接給一個路徑，例如根目錄 /，它就只回報那個路徑所在的檔案系統。"),
    R("gdf /"),
    S("你不必知道裝置名稱，df 會自己往上找到對應的掛載點，輸出只剩一行。"),

    CLR(key="gdf .：目前所在的目錄落在哪顆磁碟", hero="gdf .", toks=[
        ("gdf", "GNU df", "path"),
        (".", "當前工作目錄", "path")]),
    S("想知道現在站的這個目錄屬於哪個檔案系統，方法也一樣。"),
    S("把路徑換成一個點，代表目前的工作目錄，gdf 會解析它實際落在哪一顆磁碟上。"),
    R("gdf ."),
    S("在 macOS 上，使用者資料其實住在一個獨立的 Data 卷，這一招能立刻看穿。"),

    CLR(key="-h 與路徑組合：好讀地只看一顆磁碟", hero="gdf -h /", toks=[
        ("gdf", "GNU df", "path"),
        ("-h", "人類可讀", "star"),
        ("/", "只看根目錄", "path")]),
    S("旗標和路徑其實是可以自由組合在一起的。"),
    S("把 -h 和根目錄 / 寫在一起，就能用人類可讀的方式只看那一顆磁碟。"),
    R("gdf -h /"),
    S("這是日常查單一磁碟還剩多少空間時，最順手也最好讀的寫法。"),

    CLR(key="-P：POSIX 可攜格式，欄位固定不換行", hero="gdf -P /", toks=[
        ("gdf", "GNU df", "path"),
        ("-P", "portability：固定欄位的可攜格式", "star"),
        ("/", "目標檔案系統", "path")]),
    S("要在腳本裡解析 df 的輸出時，最怕欄位排版在不同系統上跑掉。"),
    S("這時補上 -P 旗標，輸出就會切換成欄位固定、跨系統一致的可攜格式。"),
    R("gdf -P /"),
    S("不論換到哪一台機器執行，欄位的位置都一樣，最適合丟給程式解析。"),

    CLR(key="-l：只列出本機的檔案系統", hero="gdf -l", toks=[
        ("gdf", "GNU df", "path"),
        ("-l", "local：濾掉遠端掛載，只看本機", "star")]),
    S("最後，如果機器上掛了網路磁碟，有時我們只想看本機的就好。"),
    S("-l 旗標會把 NFS、SMB 這類遠端掛載過濾掉，只留下本機的檔案系統。"),
    R("gdf -l"),
    S("從一行 gdf 到這一連串旗標，你已經能把磁碟容量和 inode 用量都看得清清楚楚了。"),
]
