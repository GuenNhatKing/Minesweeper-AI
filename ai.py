from core import Game, GameState, CellState
from enum import Enum

class Action(Enum):
    PROBE = 'probe'
    FLAG = 'flag'

class AI:
    def __init__(self):
        self.game: Game = None  
        self.actions: set[tuple[tuple[int, int], Action]] = set()
        self.frontier: set[tuple[int, int]] = set()
        self.snapshot: list[list[CellState]] = None
        self.observer_task: list[list[(int, int)]] = None
        self.observer_first = None
        
    def check_rule_1(self, x, y):
        mines_count = self.game.adjacent_mines(x, y)
        flags_count = self.game.adjacent_flagged(x, y)
        if mines_count == flags_count:
            for i, j in self.game.neighbors(x, y):
                if self.game.get_cell(i, j).state == CellState.UNPROBED:
                    self.actions.add(((i, j), Action.PROBE))
            return True
        return False

    def check_rule_2(self, x, y):
        mines_count = self.game.adjacent_mines(x, y)
        unprobed_count = self.game.adjacent_unprobed(x, y)
        flags_count = self.game.adjacent_flagged(x, y)
        if mines_count == unprobed_count + flags_count:
            for i, j in self.game.neighbors(x, y):
                if self.game.get_cell(i, j).state == CellState.UNPROBED:
                    self.actions.add(((i, j), Action.FLAG))
            return True
        return False

    def check_rule_3(self, xa, ya):
        changed = False
        mines_A_count = self.game.adjacent_mines(xa, ya)
        for xb, yb in self.game.neighbors(xa, ya, 2):
            if self.game.get_cell(xb, yb).state != CellState.PROBED:
                continue
            mines_B_count = self.game.adjacent_mines(xb, yb)
            unprobed_count = 0
            flags_count = 0
            for x, y in self.game.unshared_neighbors(xb, yb, xa, ya):
                if self.game.get_cell(x, y).state == CellState.UNPROBED:
                    unprobed_count += 1
                if self.game.get_cell(x, y).state == CellState.FLAGGED:
                    flags_count += 1

            if mines_A_count == (mines_B_count - unprobed_count - flags_count):  
                for x, y in self.game.unshared_neighbors(xa, ya, xb, yb):
                    if self.game.get_cell(x, y).state == CellState.UNPROBED:
                        self.actions.add(((x, y), Action.PROBE))
                changed = True
        return changed

    def check_rule_4(self, xa, ya):
        changed = False
        mines_A_count = self.game.adjacent_mines(xa, ya)
        for xb, yb in self.game.neighbors(xa, ya, 2):
            if self.game.get_cell(xb, yb).state != CellState.PROBED:
                continue
            mines_B_count = self.game.adjacent_mines(xb, yb)
            unprobed_count = 0
            flags_count = 0
            for x, y in self.game.unshared_neighbors(xa, ya, xb, yb):
                if self.game.get_cell(x, y).state == CellState.UNPROBED:
                    unprobed_count += 1
                if self.game.get_cell(x, y).state == CellState.FLAGGED:
                    flags_count += 1

            if mines_B_count == (mines_A_count - unprobed_count - flags_count):  
                for x, y in self.game.unshared_neighbors(xa, ya, xb, yb):
                    if self.game.get_cell(x, y).state == CellState.UNPROBED:
                        self.actions.add(((x, y), Action.FLAG))
                changed = True
        return changed

    def infer(self):
        changed = False
        if not self.game.state == GameState.PLAYING:
            return False

        while self.frontier:
            x, y = self.frontier.pop()
            if self.game.get_cell(x, y).state == CellState.PROBED:
                changed |= self.check_rule_1(x, y)
                changed |= self.check_rule_2(x, y)
                changed |= self.check_rule_3(x, y)
                changed |= self.check_rule_4(x, y)

        return changed

    def reset(self):
        self.actions.clear()
        self.frontier.clear()
        self.snapshot = [[self.game.get_cell(i, j).state for i in range(self.game.w)] for j in range(self.game.h)]
        self.observer_task = [[None for i in range(self.game.w)] for j in range(self.game.h)]
        for j in range(self.game.h):
            for i in range(self.game.w):
                k = j * self.game.w + i
                next_j = (k + 1) // self.game.w
                next_i = (k + 1) % self.game.w
                if next_j < self.game.h and next_i < self.game.w:
                    self.observer_task[j][i] = (next_j, next_i)
        self.observer_first = (0, 0)

    def observe_changes(self):
        change = False
        observer_pos = self.observer_first
        observer_prev = None
        num_observed = 0
        while observer_pos:
            num_observed += 1
            j, i = observer_pos
            if self.game.get_cell(i, j).state != self.snapshot[j][i]:
                self.snapshot[j][i] = self.game.get_cell(i, j).state
                if self.game.get_cell(i, j).state == CellState.PROBED and self.game.adjacent_unprobed(i, j):
                    self.frontier.add((i, j))
                for nx, ny in self.game.neighbors(i, j):
                    if self.game.get_cell(nx, ny).state == CellState.PROBED and self.game.adjacent_unprobed(nx, ny):
                        self.frontier.add((nx, ny))
                change = True
            if observer_prev:
                if self.game.get_cell(i, j).state != CellState.UNPROBED:
                    self.observer_task[observer_prev[0]][observer_prev[1]] = self.observer_task[j][i]
            else:
                self.observer_first = self.observer_task[j][i]
            observer_prev = observer_pos
            observer_pos = self.observer_task[j][i]
        # print(f"Observed {num_observed} cells.")
        return change
    
    def make_move(self):
        if self.game.state == GameState.INITIALIZED:
            self.reset()
        if self.game.state == GameState.PLAYING and not len(self.actions):
            if self.observe_changes(): 
                self.infer()
        if self.game.state == GameState.PLAYING and len(self.actions):
            ft = self.actions.pop()
            x, y = ft[0]
            action = ft[1]
            if self.game.get_cell(x, y).state == CellState.UNPROBED:
                if action == Action.PROBE:
                    self.game.click(x, y)
                elif action == Action.FLAG:
                    self.game.click(x, y, right=True)    