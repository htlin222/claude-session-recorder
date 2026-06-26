"""Lesson: ifconfig — 在 macOS 上查看網路介面與每個欄位.

Same tool-agnostic engine as jq/rsync; only this file + setup.sh are ifconfig-
specific. Each scene dissects a read-only `ifconfig …` command (often piped to
grep/ghead to trim the output) and the explain sentence right before each R()
names the scene's token VERBATIM, so the panel reveal lands in typing-sync.

PLATFORM NOTES (this renders on macOS, BSD ifconfig):
  * ifconfig here is the BSD build; its output (hex netmask, flags=…<…>, media
    lines) differs from Linux. The intro flags this and points Linux users at
    `ip addr`. We stay strictly READ-ONLY — no interface is ever modified.
  * head on macOS is BSD/variant and differs from Linux, so every truncation
    uses `ghead` (GNU coreutils). On Linux it's the bare `head`; the intro says
    so. grep is used as-is (matches Linux). The interface output reflects this
    machine's real lo0/en0, which renders stably and non-interactively.
"""
from clipkit import S, R, CLR

SLUG = "ifconfig"
TITLE = "ifconfig 教學 · 在 macOS 上查看網路介面與欄位"

SCRIPT = [
    CLR(key="ifconfig · 在 macOS 上檢視網路介面"),
    S("每台電腦都連著網路，而 ifconfig 就是在終端機裡查看網路介面設定的經典工具。"),
    S("要先提醒的是，這裡的 ifconfig 是 macOS 上的 BSD 版本，輸出格式和 Linux 上的不太一樣。"),
    S("在 Linux 上現在大多改用 ip addr 這個指令，欄位排版會跟這支影片看到的不同。"),
    S("這支影片全程只做唯讀檢視，不會去修改任何一張網路卡的設定。"),
    S("另外有些長輸出我們會搭配 ghead 來截斷，它是 GNU 版的 head；在 Linux 上你直接打 head 就好，macOS 內建的 head 行為略有差異。"),
    S("好，我們先從怎麼把所有介面列出來開始。"),

    CLR(key="-l：只列出所有介面的名字", hero="ifconfig -l", toks=[
        ("ifconfig", "BSD 版的網路介面檢視工具", "path"),
        ("-l", "只列出介面的名字，不印細節", "star")]),
    S("直接執行 ifconfig 會一次吐出全部介面的細節，資訊量其實很大。"),
    S("如果只想知道這台機器上到底有哪些介面，可以加上 -l 這個旗標。"),
    R("ifconfig -l"),
    S("它只印出每個介面的名字，像 lo0、en0 這些，一行就看完了，是認識一台陌生機器最快的起手式。"),

    CLR(key="-a：印出每個介面的完整資訊", hero="ifconfig -a | ghead -n 14", toks=[
        ("-a", "印出所有介面的完整欄位", "star"),
        ("ghead", "GNU 版的 head", "ord"),
        ("-n 14", "只取前 14 行", "ord")]),
    S("知道名字之後，下一步是看每個介面的完整內容。"),
    S("加上 -a，ifconfig 會把所有介面的詳細欄位一次全部印出來。"),
    S("因為輸出很長，我們用 ghead 接在後面，配合 -n 14 只取前 14 行來看。"),
    R("ifconfig -a | ghead -n 14"),
    S("畫面上一次出現好幾個介面，每個都帶著自己的 flags、mtu 跟位址資訊。"),

    CLR(key="lo0：每台機器都有的回送介面", hero="ifconfig lo0", toks=[
        ("lo0", "回送介面 loopback", "star")]),
    S("從這裡開始，我們把焦點放到單一介面上。"),
    S("第一個值得認識的是 lo0，它是每台機器都有的回送介面。"),
    R("ifconfig lo0"),
    S("它的位址固定是 127.0.0.1，也就是常說的 localhost，封包送進去會直接繞回自己。"),
    S("任何在本機自己跟自己溝通的程式，走的都是這條 lo0。"),

    CLR(key="en0：對外連線的主要介面", hero="ifconfig en0", toks=[
        ("en0", "對外連線的主要介面", "star")]),
    S("真正連到外面世界的，通常是 en0 這張介面。"),
    S("在大多數的 Mac 上，en0 就是內建的乙太網路或無線網卡。"),
    R("ifconfig en0"),
    S("這一大段就是 en0 的完整設定，接下來我們會逐一拆解裡面的每個欄位。"),

    CLR(key="flags：介面的狀態旗標 UP/RUNNING", hero="ifconfig en0 | ghead -n 1",
        toks=[
        ("ghead", "GNU 版的 head", "ord"),
        ("-n 1", "只取第一行", "star")]),
    S("先看 en0 的第一行，那一行就濃縮了介面最重要的狀態。"),
    S("我們用 ghead 配合 -n 1，只把開頭那一行抓出來。"),
    R("ifconfig en0 | ghead -n 1"),
    S("行首那串 flags 就是介面的狀態旗標，UP 代表已啟用、RUNNING 代表正在運作。"),

    CLR(key="mtu：單一封包的最大位元組數",
        hero="ifconfig en0 | grep -o 'mtu [0-9]*'", toks=[
        ("grep", "逐行過濾輸出", "ord"),
        ("-o", "只印出比對到的片段", "ord"),
        ("mtu", "單一封包的最大位元組數", "star")]),
    S("第一行裡還藏著一個小數字，叫做 mtu。"),
    S("我們用 grep 搭配 -o，只把 mtu 那一小段精準地抓出來。"),
    R("ifconfig en0 | grep -o 'mtu [0-9]*'"),
    S("mtu 是單一封包能裝的最大位元組數，乙太網路上常見的值是 1500。"),

    CLR(key="inet：這個介面的 IPv4 位址",
        hero="ifconfig en0 | grep 'inet '", toks=[
        ("grep", "過濾出含關鍵字的行", "ord"),
        ("inet", "這個介面的 IPv4 位址", "star")]),
    S("接下來是大家最關心的，這台機器的 IP 位址。"),
    S("把 en0 的輸出交給 grep，只留下含有 inet 的那一行。"),
    R("ifconfig en0 | grep 'inet '"),
    S("inet 後面那組數字就是這個介面的 IPv4 位址，也是區域網路裡找到你的門牌。"),
    S("注意我們在 inet 後面特意留了一個空格，就是為了避開 inet6 那幾行。"),

    CLR(key="netmask：劃分網段的子網路遮罩",
        hero="ifconfig en0 | grep -o 'netmask 0x[0-9a-f]*'", toks=[
        ("grep", "逐行過濾", "ord"),
        ("-o", "只取比對到的片段", "ord"),
        ("netmask", "劃分網段的子網路遮罩", "star")]),
    S("跟 IP 位址形影不離的，是子網路遮罩。"),
    S("一樣用 grep 加上 -o，把 netmask 那一段單獨抽出來。"),
    R("ifconfig en0 | grep -o 'netmask 0x[0-9a-f]*'"),
    S("netmask 決定 IP 位址裡哪部分是網段、哪部分是主機，BSD 這裡用十六進位的 0x 表示，Linux 則常寫成點分的形式。"),

    CLR(key="inet6：這個介面的 IPv6 位址",
        hero="ifconfig en0 | grep inet6", toks=[
        ("grep", "過濾出該欄位", "ord"),
        ("inet6", "這個介面的 IPv6 位址", "star")]),
    S("現在的網路同時也跑 IPv6，對應的欄位叫做 inet6。"),
    S("用 grep 過濾 inet6，就能看到這個介面所有的 IPv6 位址。"),
    R("ifconfig en0 | grep inet6"),
    S("開頭是 fe80 的那一條是 link-local 位址，只在這個區域網段內有效。"),

    CLR(key="ether：網路卡的 MAC 硬體位址",
        hero="ifconfig en0 | grep ether", toks=[
        ("grep", "過濾出該欄位", "ord"),
        ("ether", "網路卡的 MAC 硬體位址", "star")]),
    S("位址聊得差不多了，我們往實體層再靠近一點。"),
    S("用 grep 找出 ether 這一行，看的是網路卡的硬體位址。"),
    R("ifconfig en0 | grep ether"),
    S("ether 後面那組六段十六進位數字，就是俗稱的 MAC 位址，幾乎是全世界獨一無二的。"),

    CLR(key="status：介面目前是否在線",
        hero="ifconfig en0 | grep status", toks=[
        ("grep", "過濾出該欄位", "ord"),
        ("status", "介面目前是否在線", "star")]),
    S("知道是哪張卡之後，我們會想確認它現在到底通不通。"),
    S("grep 出 status 這一行，就能看出介面當前的連線狀態。"),
    R("ifconfig en0 | grep status"),
    S("status 顯示 active 代表線路是通的，如果是 inactive 就表示沒接上。"),

    CLR(key="media：實體連線的速率與型態",
        hero="ifconfig en0 | grep media", toks=[
        ("grep", "過濾出該欄位", "ord"),
        ("media", "實體連線的速率與型態", "star")]),
    S("最後一個欄位，是關於這條線實際能跑多快。"),
    S("用 grep 把 media 這一行抓出來，看的是實體連線的型態與速率。"),
    R("ifconfig en0 | grep media"),
    S("media 會告訴你協商出來的速度，例如 1000baseT 就是常見的 gigabit 乙太網路。"),
    S("從列出介面到讀懂每個欄位，現在你已經能完整看懂一張網卡的設定了。"),
]
