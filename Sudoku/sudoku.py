"""
Sudoku Game in Python (Tkinter)
--------------------------------
Single-file app with:
- 9x9 grid, 3x3 box highlights
- Number pad (1–9), Erase, Hint, Check, New Game
- Pencil mode (notes), Undo/Redo
- Live conflict highlighting (toggleable)
- Timer

Run: python sudoku.py
Requires: Python 3.x (no external libraries)
"""

import random
import time
import tkinter as tk
from tkinter import messagebox

GRID_SIZE = 9
BOX_SIZE = 3

class SudokuGenerator:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)

    def generate_full_board(self):
        board = [[0]*GRID_SIZE for _ in range(GRID_SIZE)]
        self._fill_board(board)
        return board

    def _find_empty(self, board):
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if board[r][c] == 0:
                    return r, c
        return None

    def _valid(self, board, r, c, val):
        # Row/Col
        for i in range(GRID_SIZE):
            if board[r][i] == val: return False
            if board[i][c] == val: return False
        # Box
        br = (r // BOX_SIZE) * BOX_SIZE
        bc = (c // BOX_SIZE) * BOX_SIZE
        for i in range(br, br+BOX_SIZE):
            for j in range(bc, bc+BOX_SIZE):
                if board[i][j] == val:
                    return False
        return True

    def _fill_board(self, board):
        empty = self._find_empty(board)
        if not empty:
            return True
        r, c = empty
        nums = list(range(1, 10))
        self.rng.shuffle(nums)
        for n in nums:
            if self._valid(board, r, c, n):
                board[r][c] = n
                if self._fill_board(board):
                    return True
                board[r][c] = 0
        return False

    def _copy(self, board):
        return [row[:] for row in board]

    def _count_solutions(self, board, limit=2):
        # Backtracking solver that counts up to `limit` solutions
        empty = None
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if board[r][c] == 0:
                    empty = (r, c)
                    break
            if empty:
                break
        if not empty:
            return 1
        r, c = empty

        count = 0
        for n in range(1, 10):
            if self._valid(board, r, c, n):
                board[r][c] = n
                count += self._count_solutions(board, limit)
                board[r][c] = 0
                if count >= limit:
                    return count
        return count

    def generate_puzzle(self, difficulty="medium"):
        # Difficulty -> approx number of givens
        # easy: ~40-45, medium: ~32-38, hard: ~26-31
        targets = {
            "easy": self.rng.randint(40, 45),
            "medium": self.rng.randint(32, 38),
            "hard": self.rng.randint(26, 31),
            "expert": self.rng.randint(22, 26),
        }
        givens_target = targets.get(difficulty, targets["medium"])

        full = self.generate_full_board()
        puzzle = self._copy(full)

        # Create a list of positions and try removing symmetrically while preserving uniqueness
        cells = [(r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE)]
        self.rng.shuffle(cells)

        def symmetric(r, c):
            return GRID_SIZE - 1 - r, GRID_SIZE - 1 - c

        removed = 0
        # Try removing until the number of givens reaches target
        to_remove = GRID_SIZE*GRID_SIZE - givens_target
        for (r, c) in cells:
            if puzzle[r][c] == 0:
                continue
            r2, c2 = symmetric(r, c)
            if (r2, c2) == (r, c):
                pair = [(r, c)]
            else:
                pair = [(r, c), (r2, c2)]

            backup = [puzzle[x][y] for x, y in pair]
            for x, y in pair:
                puzzle[x][y] = 0

            board_copy = self._copy(puzzle)
            if self._count_solutions(board_copy, limit=2) != 1:
                # Not unique; revert
                for (x, y), val in zip(pair, backup):
                    puzzle[x][y] = val
            else:
                removed += len(pair)
                if removed >= to_remove:
                    break

        return puzzle, full

class SudokuApp:
    CELL_BG = "#ffffff"
    CELL_BG_LOCKED = "#f2f2f2"
    CELL_BG_SELECTED = "#cfe8ff"
    CELL_BG_HIGHLIGHT = "#eaf3ff"
    CELL_BG_CONFLICT = "#ffdddd"
    GRID_LINE = "#000000"

    def __init__(self, root):
        self.root = root
        self.root.title("Sudoku — Python Tkinter")
        self.generator = SudokuGenerator()

        self.puzzle = None
        self.solution = None
        self.values = [[0]*GRID_SIZE for _ in range(GRID_SIZE)]
        self.locked = [[False]*GRID_SIZE for _ in range(GRID_SIZE)]
        self.notes = [[set() for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

        self.selected = (0, 0)
        self.pencil_mode = tk.BooleanVar(value=False)
        self.live_conflicts = tk.BooleanVar(value=True)

        self.undo_stack = []
        self.redo_stack = []

        self.start_time = time.time()
        self.timer_running = True

        self._build_ui()
        self.new_game("medium")
        self._tick_timer()

    def _build_ui(self):
        top = tk.Frame(self.root)
        top.pack(padx=10, pady=10)

        # Left: board
        self.board_frame = tk.Frame(top)
        self.board_frame.grid(row=0, column=0, padx=(0, 10))

        self.cells = []
        for r in range(GRID_SIZE):
            row_cells = []
            for c in range(GRID_SIZE):
                f = tk.Frame(self.board_frame, width=50, height=50, bd=1, relief=tk.SOLID, bg=self.CELL_BG)
                f.grid(row=r, column=c, sticky="nsew")
                f.grid_propagate(False)
                lbl = tk.Label(f, text="", font=("Segoe UI", 16), bg=self.CELL_BG)
                lbl.place(relx=0.5, rely=0.5, anchor="center")
                f.bind("<Button-1>", lambda e, rr=r, cc=c: self.select(rr, cc))
                lbl.bind("<Button-1>", lambda e, rr=r, cc=c: self.select(rr, cc))
                row_cells.append((f, lbl))
            self.cells.append(row_cells)

        # Thicker lines for 3x3 boxes
        for i in range(GRID_SIZE):
            self.board_frame.grid_rowconfigure(i, weight=1)
            self.board_frame.grid_columnconfigure(i, weight=1)
        for i in range(0, GRID_SIZE+1):
            if i % BOX_SIZE == 0 and i != 0 and i != GRID_SIZE:
                # draw horizontal and vertical separators by adding padding
                for c in range(GRID_SIZE):
                    f, _ = self.cells[i-1][c]
                    f.configure(highlightbackground=self.GRID_LINE, highlightthickness=1)
                for r in range(GRID_SIZE):
                    f, _ = self.cells[r][i-1]
                    f.configure(highlightbackground=self.GRID_LINE, highlightthickness=1)

        # Right: controls
        right = tk.Frame(top)
        right.grid(row=0, column=1, sticky="n")

        self.timer_label = tk.Label(right, text="00:00", font=("Segoe UI", 14))
        self.timer_label.pack(pady=(0, 8))

        keypad = tk.Frame(right)
        keypad.pack(pady=4)
        for i in range(1, 10):
            b = tk.Button(keypad, text=str(i), width=4, height=2, command=lambda n=i: self.input_number(n))
            r = (i-1)//3
            c = (i-1)%3
            b.grid(row=r, column=c, padx=2, pady=2)

        actions = tk.Frame(right)
        actions.pack(pady=(8, 4))

        tk.Button(actions, text="Erase", width=10, command=self.erase).grid(row=0, column=0, padx=2, pady=2)
        tk.Button(actions, text="Hint", width=10, command=self.hint).grid(row=0, column=1, padx=2, pady=2)
        tk.Button(actions, text="Check", width=10, command=self.check_solution).grid(row=1, column=0, padx=2, pady=2)
        tk.Button(actions, text="New", width=10, command=lambda: self.new_game("medium")).grid(row=1, column=1, padx=2, pady=2)
        tk.Button(actions, text="Undo", width=10, command=self.undo).grid(row=2, column=0, padx=2, pady=2)
        tk.Button(actions, text="Redo", width=10, command=self.redo).grid(row=2, column=1, padx=2, pady=2)

        toggles = tk.Frame(right)
        toggles.pack(pady=(6, 0))
        tk.Checkbutton(toggles, text="Pencil mode", variable=self.pencil_mode).grid(row=0, column=0, sticky="w")
        tk.Checkbutton(toggles, text="Live conflicts", variable=self.live_conflicts, command=self.refresh_view).grid(row=1, column=0, sticky="w")

        # Keyboard bindings
        self.root.bind("<Key>", self._on_key)

    def format_time(self, seconds):
        m = int(seconds) // 60
        s = int(seconds) % 60
        return f"{m:02d}:{s:02d}"

    def _tick_timer(self):
        if self.timer_running:
            elapsed = time.time() - self.start_time
            self.timer_label.config(text=self.format_time(elapsed))
        self.root.after(500, self._tick_timer)

    def new_game(self, difficulty="medium"):
        self.puzzle, self.solution = self.generator.generate_puzzle(difficulty)
        self.values = [row[:] for row in self.puzzle]
        self.locked = [[self.puzzle[r][c] != 0 for c in range(GRID_SIZE)] for r in range(GRID_SIZE)]
        self.notes = [[set() for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.selected = (0, 0)
        self.start_time = time.time()
        self.timer_running = True
        self.refresh_view()

    def select(self, r, c):
        self.selected = (r, c)
        self.refresh_view()

    def _record_action(self, r, c, prev_val, new_val, prev_notes, new_notes):
        self.undo_stack.append((r, c, prev_val, new_val, prev_notes.copy(), new_notes.copy()))
        self.redo_stack.clear()

    def input_number(self, n):
        r, c = self.selected
        if self.locked[r][c]:
            return
        prev_val = self.values[r][c]
        prev_notes = self.notes[r][c].copy()
        if self.pencil_mode.get():
            # Toggle note
            if n in self.notes[r][c]:
                self.notes[r][c].remove(n)
            else:
                self.notes[r][c].add(n)
            self._record_action(r, c, prev_val, prev_val, prev_notes, self.notes[r][c])
        else:
            self.values[r][c] = n
            self.notes[r][c].clear()
            self._record_action(r, c, prev_val, n, prev_notes, set())
        self.refresh_view()

    def erase(self):
        r, c = self.selected
        if self.locked[r][c]:
            return
        prev_val = self.values[r][c]
        prev_notes = self.notes[r][c].copy()
        self.values[r][c] = 0
        self.notes[r][c].clear()
        self._record_action(r, c, prev_val, 0, prev_notes, set())
        self.refresh_view()

    def undo(self):
        if not self.undo_stack:
            return
        r, c, prev_val, new_val, prev_notes, new_notes = self.undo_stack.pop()
        # Save inverse to redo
        self.redo_stack.append((r, c, self.values[r][c], prev_val, self.notes[r][c].copy(), prev_notes.copy()))
        self.values[r][c] = prev_val
        self.notes[r][c] = prev_notes
        self.selected = (r, c)
        self.refresh_view()

    def redo(self):
        if not self.redo_stack:
            return
        r, c, prev_val, new_val, prev_notes, new_notes = self.redo_stack.pop()
        # Save inverse back to undo
        self.undo_stack.append((r, c, self.values[r][c], new_val, self.notes[r][c].copy(), new_notes.copy()))
        self.values[r][c] = new_val
        self.notes[r][c] = new_notes
        self.selected = (r, c)
        self.refresh_view()

    def _on_key(self, event):
        key = event.keysym
        r, c = self.selected
        if key in [str(i) for i in range(1, 10)]:
            self.input_number(int(key))
        elif key in ("BackSpace", "Delete", "KP_Delete"):
            self.erase()
        elif key in ("Left", "Right", "Up", "Down"):
            dr, dc = {"Left": (0, -1), "Right": (0, 1), "Up": (-1, 0), "Down": (1, 0)}[key]
            nr = (r + dr) % GRID_SIZE
            nc = (c + dc) % GRID_SIZE
            self.select(nr, nc)

    def is_conflict(self, r, c, val):
        if val == 0:
            return False
        # Check row/col conflicts
        for i in range(GRID_SIZE):
            if i != c and self.values[r][i] == val:
                return True
            if i != r and self.values[i][c] == val:
                return True
        # Box
        br = (r // BOX_SIZE) * BOX_SIZE
        bc = (c // BOX_SIZE) * BOX_SIZE
        for i in range(br, br+BOX_SIZE):
            for j in range(bc, bc+BOX_SIZE):
                if (i, j) != (r, c) and self.values[i][j] == val:
                    return True
        return False

    def refresh_view(self):
        sr, sc = self.selected
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                f, lbl = self.cells[r][c]
                base_bg = self.CELL_BG_LOCKED if self.locked[r][c] else self.CELL_BG

                # Row/col/box highlight
                if r == sr or c == sc or (r//BOX_SIZE, c//BOX_SIZE) == (sr//BOX_SIZE, sc//BOX_SIZE):
                    bg = self.CELL_BG_HIGHLIGHT
                else:
                    bg = base_bg

                if (r, c) == (sr, sc):
                    bg = self.CELL_BG_SELECTED

                # Conflict tint
                if self.live_conflicts.get() and self.is_conflict(r, c, self.values[r][c]):
                    bg = self.CELL_BG_CONFLICT

                f.configure(bg=bg)
                lbl.configure(bg=bg)

                if self.values[r][c] != 0:
                    lbl.configure(text=str(self.values[r][c]), font=("Segoe UI", 16, "bold" if self.locked[r][c] else "normal"), fg="#000000")
                else:
                    # Show notes if any
                    if self.notes[r][c]:
                        ntxt = " ".join(str(n) for n in sorted(self.notes[r][c]))
                        lbl.configure(text=ntxt, font=("Segoe UI", 10, "normal"), fg="#666666")
                    else:
                        lbl.configure(text="", font=("Segoe UI", 16), fg="#000000")

    def check_solution(self):
        # If any empty: warn
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.values[r][c] == 0:
                    messagebox.showinfo("Sudoku", "There are still empty cells.")
                    return
        if self.values == self.solution:
            self.timer_running = False
            elapsed = time.time() - self.start_time
            messagebox.showinfo("Sudoku", f"Correct! Completed in {self.format_time(elapsed)}")
        else:
            messagebox.showwarning("Sudoku", "Something's off. Check conflicts or try a hint.")

    def hint(self):
        # Fill one empty cell with correct value
        empties = [(r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE) if self.values[r][c] == 0]
        if not empties:
            return
        r, c = random.choice(empties)
        prev_val = self.values[r][c]
        prev_notes = self.notes[r][c].copy()
        self.values[r][c] = self.solution[r][c]
        self.notes[r][c].clear()
        self._record_action(r, c, prev_val, self.values[r][c], prev_notes, set())
        self.refresh_view()


def main():
    root = tk.Tk()
    app = SudokuApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
