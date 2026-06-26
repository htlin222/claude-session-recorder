"""Lesson: ssh — 不連線也能學的本機金鑰與設定.

Same tool-agnostic engine as jq/rsync; only this file + setup.sh are ssh-
specific. We teach the LOCAL, reproducible, non-interactive half of the SSH tool
family: querying the version, generating an ed25519 key pair, telling the private
key from the public key, deriving the public key back from the private one,
fingerprints + randomart, the ~/.ssh/config format, and finally `ssh -G` which
prints the resolved effective config WITHOUT ever connecting. Nothing here needs
the network; nothing touches the real ~/.ssh (setup.sh works only inside
intermediate/). The explain sentence right before each R() names the scene's
flag token VERBATIM so the panel reveal lands in typing-sync.

Platform notes (this renders on macOS):
  * `cat` here is a BSD variant; we use GNU `gcat` so output matches Linux. On
    Linux it is simply `cat`. The intro says so.
  * `ssh -V`'s tail differs: macOS links LibreSSL, Linux usually OpenSSL — the
    narration flags this so nobody is surprised.
The random key bytes / fingerprint / randomart differ per render (a fresh key is
made live), but the SHAPE of every output is stable, which is what we teach.
"""
from clipkit import S, R, CLR

SLUG = "ssh"
TITLE = "ssh 教學 · 不連線也能學的本機金鑰與設定"

SCRIPT = [
    CLR(key="ssh · 不連線也能學的金鑰與設定"),
    S("一講到 SSH，大家想到的多半是連線到遠端主機，但其實有一大半的功能，根本不需要網路。"),
    S("這支教學只碰本機、可重現、不連線的部分，全程不會動到你真正的 ~/.ssh。"),
    S("先講平台差異：這裡的 cat 是 BSD 版，所以示範一律改用 GNU 的 gcat，而在 Linux 上它就是原本的 cat。"),
    S("另外等一下 ssh -V 的後半，在 macOS 顯示的是 LibreSSL，在 Linux 通常會是 OpenSSL，這點先放在心上。"),

    CLR(key="ssh -V：查 OpenSSH 版本", hero="ssh -V", toks=[
        ("ssh", "SSH 用戶端本體", "path"),
        ("-V", "印出版本字串後立刻結束", "star")]),
    S("第一步，只要加上 -V 這個旗標，ssh 就會印出版本字串然後立刻結束，完全不會嘗試連線。"),
    R("ssh -V"),
    S("前半的 OpenSSH 版本號兩邊一致，後半的 LibreSSL 才是 macOS 特有，換到 Linux 上多半會變成 OpenSSL。"),

    CLR(key="ssh-keygen -t：產生 ed25519 金鑰對",
        hero="ssh-keygen -t ed25519 -C 'me@host' -f ./id_demo -N ''", toks=[
        ("ssh-keygen", "產生與管理金鑰的工具", "path"),
        ("-t ed25519", "選用 ed25519 演算法", "star"),
        ("-C 'me@host'", "寫進公鑰的註解", "ord"),
        ("-f ./id_demo", "指定輸出檔名", "ord"),
        ("-N ''", "設成空密碼", "ord")]),
    S("有了版本資訊，接下來正式產生一對金鑰。"),
    S("我們用 -t ed25519 指定演算法，它是現代、短小又安全的橢圓曲線選擇。"),
    S("再用 -C 'me@host' 加上一段註解，方便日後辨認這把鑰匙到底是誰的。"),
    S("最後用 -f ./id_demo 指定檔名，並用 -N '' 設成空密碼，示範才能非互動地一次跑完。"),
    R("ssh-keygen -t ed25519 -C 'me@host' -f ./id_demo -N ''"),
    S("一口氣產生了兩個檔案：沒有密碼的私鑰 id_demo，以及與它配對的公鑰 id_demo.pub。"),

    CLR(key="私鑰 id_demo：絕對不能外流", hero="gcat id_demo", toks=[
        ("gcat", "把檔案內容印到畫面", "path"),
        ("id_demo", "沒有副檔名的就是私鑰", "star")]),
    S("先看那個沒有副檔名的檔，也就是私鑰 id_demo。"),
    S("用 gcat 把 id_demo 的內容直接印出來瞧瞧。"),
    R("gcat id_demo"),
    S("開頭的 OPENSSH PRIVATE KEY 標記說明了它的身份，這把私鑰必須牢牢留在本機，絕對不能外流。"),

    CLR(key="公鑰 id_demo.pub：可以公開分享", hero="gcat id_demo.pub", toks=[
        ("gcat", "印出檔案內容", "path"),
        ("id_demo.pub", "多了 .pub 的就是公鑰", "star")]),
    S("接著看多了點 pub 的那個檔，也就是公鑰 id_demo.pub。"),
    S("一樣用 gcat 把 id_demo.pub 的單行內容印出來。"),
    R("gcat id_demo.pub"),
    S("公鑰只有一行，由演算法名稱、Base64 編碼和那段註解組成，可以放心貼到伺服器或 GitHub。"),

    CLR(key="ssh-keygen -y：從私鑰推回公鑰", hero="ssh-keygen -y -f id_demo",
        toks=[
        ("ssh-keygen", "金鑰工具", "path"),
        ("-y", "從私鑰重新導出公鑰", "star"),
        ("-f id_demo", "指定要讀的私鑰", "ord")]),
    S("萬一公鑰檔不小心被刪掉了，加上 -y 這個旗標，ssh-keygen 就會從私鑰導出對應的公鑰。"),
    S("再用 -f id_demo 指定要讀進來的那一把私鑰。"),
    R("ssh-keygen -y -f id_demo"),
    S("印出來的這一行，和剛才的 id_demo.pub 一字不差，證明公鑰本來就藏在私鑰裡面。"),

    CLR(key="ssh-keygen -l：算金鑰指紋", hero="ssh-keygen -l -f id_demo.pub",
        toks=[
        ("ssh-keygen", "金鑰工具", "path"),
        ("-l", "計算金鑰的指紋", "star"),
        ("-f id_demo.pub", "對哪個檔計算", "ord")]),
    S("金鑰本身很長不好比對，加上 -l 並用 -f id_demo.pub 指定公鑰檔，ssh-keygen 就會算出它的指紋。"),
    R("ssh-keygen -l -f id_demo.pub"),
    S("輸出依序是位元數、SHA256 指紋、註解，以及括號裡的演算法 ED25519。"),

    CLR(key="-E md5：換成舊式指紋格式",
        hero="ssh-keygen -l -E md5 -f id_demo.pub", toks=[
        ("-l", "算指紋", "ord"),
        ("-E md5", "改用舊式的 MD5 格式顯示", "star"),
        ("-f id_demo.pub", "目標公鑰", "path")]),
    S("新版預設用 SHA256 顯示指紋，但有些舊系統或文件還停留在 MD5。"),
    S("在 -l 之外再加上 -E md5，就能把指紋切換成舊式的格式。"),
    R("ssh-keygen -l -E md5 -f id_demo.pub"),
    S("這次指紋變成一串以冒號分隔的十六進位，正是以前最常見到的那種樣子。"),

    CLR(key="ssh-keygen -v：畫出指紋的 randomart",
        hero="ssh-keygen -lv -f id_demo.pub", toks=[
        ("ssh-keygen", "金鑰工具", "path"),
        ("-lv", "算指紋時再加 -v 畫出 randomart", "star"),
        ("-f id_demo.pub", "目標公鑰", "path")]),
    S("指紋還能畫成圖，把旗標合併寫成 -lv，就是在算指紋的同時，再用 -v 把 randomart 一起印出來。"),
    R("ssh-keygen -lv -f id_demo.pub"),
    S("這張由符號排成的方塊就是 randomart，同一把金鑰永遠會畫出一模一樣的圖案。"),

    CLR(key="~/.ssh/config：用 Host 區塊描述主機", hero="gcat config", toks=[
        ("gcat", "印出檔案內容", "path"),
        ("config", "SSH 的用戶端設定檔", "star")]),
    S("每次都打一長串參數太累，先用 gcat 看看這個示範用的 config 設定檔長什麼樣子。"),
    R("gcat config"),
    S("檔案裡用 Host 區塊替一組連線參數取個短名，例如把 web 對應到真正的主機、使用者與連接埠。"),

    CLR(key="ssh -G：印出解析後的有效設定（不連線）",
        hero="ssh -G web -F ./config", toks=[
        ("ssh", "SSH 用戶端", "path"),
        ("-G", "印出解析後的設定但不連線", "star"),
        ("web", "要查詢的主機別名", "path"),
        ("-F ./config", "指定要讀的設定檔", "ord")]),
    S("寫好 config 之後，怎麼確認 ssh 真的會照我們想的方式去解析它？"),
    S("用 -G 這個旗標，ssh 會針對某一台主機印出解析後的完整設定，而且全程不連線。"),
    S("後面接上主機別名 web，再用 -F ./config 指定要讀的就是手邊這個設定檔。"),
    R("ssh -G web -F ./config"),
    S("輸出裡的 hostname、user、port 正是我們在 config 寫下的值，其餘則是系統的預設。"),

    CLR(key="ssh-keygen -R：從 known_hosts 移除主機（破壞性）",
        hero="ssh-keygen -R oldserver -f known_hosts", toks=[
        ("ssh-keygen", "金鑰工具", "path"),
        ("-R", "移除某主機的已知金鑰", "star"),
        ("oldserver", "要移除的主機名稱", "path"),
        ("-f known_hosts", "指定 known_hosts 檔", "ord")]),
    S("最後這個會真的改寫檔案，請特別小心：伺服器換金鑰跳警告時，可以用 -R 把舊記錄從 known_hosts 裡移除。"),
    S("這裡刻意用 -f known_hosts 指向示範檔，所以完全不會碰到你真正家目錄裡的記錄。"),
    R("ssh-keygen -R oldserver -f known_hosts"),
    S("執行之後它會刪掉 oldserver 對應的那一整行，並貼心地把原本的內容備份成 known_hosts.old。"),
    S("從查版本、產生金鑰到讀 config、解析設定，這些不連線就能練的基本功，就是你日後順利連上遠端的底氣。"),
]
