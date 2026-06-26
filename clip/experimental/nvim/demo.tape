# PROVEN recipe: VHS driving nvim to write + run a file.
# Render from this dir:  vhs demo.tape   (-> out.mp4)
# Reuse: copy code.py target name + init.vim; keep the Escape-before-i and the
# Sleeps. Type each line then Enter; literal indentation is preserved because the
# init disables autoindent.
Output out.mp4
Set Shell zsh
Set FontSize 26
Set Width 1200
Set Height 1080
Set Theme "Catppuccin Mocha"
Set Padding 30
Set TypingSpeed 55ms

Hide
Type "clear"
Enter
Show
Sleep 500ms

Type "nvim -u init.vim code.py"
Enter
Sleep 1.8s

Escape
Sleep 300ms
Type "i"
Sleep 400ms

Type "def fib(n):"
Enter
Type "    a, b = 0, 1"
Enter
Type "    for _ in range(n):"
Enter
Type "        a, b = b, a + b"
Enter
Type "    return a"
Enter
Type "print([fib(i) for i in range(10)])"

Escape
Sleep 700ms
Type ":wq"
Enter
Sleep 800ms

Type "python3 code.py"
Enter
Sleep 1.5s
