from pathlib import Path

import pygame
import itertools
import random
from enum import Enum
from typing import Iterable


GAME_NAME = "PySET"
DEFAULT_SCALE = 0.5


def main():
    view = SetGameView()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            elif event.type == pygame.MOUSEBUTTONUP:
                view.handle_click(event)
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_n:
                    view.new_game()
                elif event.key == pygame.K_c:
                    view.reset_selected()
                    view.redraw()
                elif event.key == pygame.K_a:
                    view.toggle_available()
        pygame.time.wait(10)


class SetGameView:
    def __init__(self, scale=DEFAULT_SCALE):
        self.game = SetGame()
        self._load_images(scale)
        size = (6 * self._card_size[0], 3 * self._card_size[1])
        self._screen = pygame.display.set_mode(size)
        self._scale = scale
        self._show_available = False
        self.reset_selected()
        self.redraw()

    def new_game(self):
        self.game = SetGame()
        self.reset_selected()
        self.redraw()

    @property
    def _ncol(self):
        return len(self.game.active_cards) // 3

    def reset_selected(self):
        self._selected = [[False for _ in range(self._ncol)] for _ in range(3)]
        self._num_selected = 0

    def _load_images(self, scale):
        self._images = {}
        for path in Path("png").iterdir():
            if path.is_file() and path.suffix == ".png":
                name = path.name.split(".")[0]
                img = pygame.image.load(str(path))
                img = pygame.transform.scale(
                    img, tuple(map(lambda s: int(s * scale), img.get_size()))
                )
                self._images[name] = img
        self._card_size = img.get_size()
        self._shading = pygame.mask.from_surface(img).to_surface(
            setcolor=pygame.Color(0, 0, 0, 96), unsetcolor=None
        )

    def _check_selected(self):
        cards = self.game.active_cards
        scards = [
            card
            for card, (row, col) in zip(
                cards, itertools.product(range(3), range(self._ncol))
            )
            if self._selected[row][col]
        ]
        assert len(scards) == 3
        try:
            self.game.remove_set(*scards)
        except ValueError:
            return
        else:
            self._selected = [[False for _ in range(self._ncol)] for _ in range(3)]
            self._num_selected = 0
            self.redraw()

    def handle_click(self, event):
        if self.game.state == State.GAME_OVER:
            return
        img = next(iter(self._images.values()))
        for row in range(3):
            for col in range(self._ncol):
                disp_col = col + 0.5 * (6 - self._ncol)
                loc = (self._card_size[0] * disp_col, self._card_size[1] * row)
                if img.get_rect(left=loc[0], top=loc[1]).collidepoint(event.pos):
                    self._selected[row][col] = not self._selected[row][col]
                    if self._selected[row][col]:
                        self._num_selected += 1
                    else:
                        self._num_selected -= 1
                    if self._num_selected == 3:
                        self._check_selected()
                    self.redraw()
                    return

    def toggle_available(self):
        self._show_available = not self._show_available
        self.redraw()

    def redraw(self):
        if self.game.state == State.IN_GAME:
            found = len(self.game.solved_sets) * 3
            if self._show_available:
                moves = list(find_triples(self.game.active_cards))
                available = f", available: {len(moves)}"
            else:
                available = ""
            remaining = self.game.deck_remaining + len(self.game.active_cards)
            pygame.display.set_caption(
                f"{GAME_NAME} (found: {found}, remaining: {remaining}{available})"
            )
        else:
            pygame.display.set_caption(f"{GAME_NAME} (game over - press N to restart)")
        self._screen.fill((192, 192, 192))
        cards = self.game.active_cards
        for card, (row, col) in zip(
            cards, itertools.product(range(3), range(self._ncol))
        ):
            img = self._images[card.to_shorthand()]
            disp_col = col + 0.5 * (6 - self._ncol)
            loc = (img.get_width() * disp_col, img.get_height() * row)
            self._screen.blit(img, loc)
            if self._selected[row][col]:
                self._screen.blit(self._shading, loc)

        pygame.display.flip()


class Number(Enum):

    ONE = 1
    TWO = 2
    THREE = 3


class Color(Enum):

    RED = "red"
    GREEN = "green"
    PURPLE = "purple"


class Shading(Enum):

    EMPTY = "empty"
    FILLED = "filled"
    HATCHED = "hatched"


class Symbol(Enum):

    SQUIGGLE = "squiggle"
    DIAMOND = "diamond"
    OVAL = "oval"


SHORTHAND_MAP = {
    "1": Number.ONE,
    "2": Number.TWO,
    "3": Number.THREE,
    "r": Color.RED,
    "g": Color.GREEN,
    "p": Color.PURPLE,
    "e": Shading.EMPTY,
    "f": Shading.FILLED,
    "h": Shading.HATCHED,
    "d": Symbol.DIAMOND,
    "s": Symbol.SQUIGGLE,
    "o": Symbol.OVAL,
}
REVERSE_SHORTHAND = {v: k for k, v in SHORTHAND_MAP.items()}


class Card:

    properties = ("number", "color", "shading", "symbol")

    def __init__(self, number: Number, color: Color, shading: Shading, symbol: Symbol):
        self.number = number
        self.color = color
        self.shading = shading
        self.symbol = symbol

    @classmethod
    def from_shorthand(cls, shorthand: str):
        if len(shorthand) != 4:
            raise ValueError("invalid length")
        params = {
            type(SHORTHAND_MAP[c]).__name__.lower(): SHORTHAND_MAP[c] for c in shorthand
        }
        return Card(**params)

    def __repr__(self):
        return f'<Card({", ".join(str(getattr(self, p)) for p in self.properties)})>'

    def __eq__(self, other):
        if not isinstance(other, Card):
            return False
        conditions = (getattr(self, p) == getattr(other, p) for p in self.properties)
        return all(conditions)

    def __hash__(self):
        return hash(tuple((getattr(self, p) for p in self.properties)))

    def to_shorthand(self):
        return "".join((REVERSE_SHORTHAND[getattr(self, p)] for p in self.properties))

    def complement(self, other: "Card"):
        if self == other:
            return None
        new_properties = {}
        for p in self.properties:
            val1 = getattr(self, p)
            val2 = getattr(other, p)
            if val1 == val2:
                new_properties[p] = val1
            else:
                (new_properties[p],) = set(type(val1)) - {val1, val2}
        return Card(**new_properties)


def find_triples(cards: Iterable[Card]):
    card_list = list(cards)
    for i, card1 in enumerate(card_list):
        for j, card2 in enumerate(card_list[i + 1 :], start=i + 1):
            if card1 == card2:
                raise Exception(f"duplicate card found: {card1}")
            card3 = card1.complement(card2)
            if card3 in card_list[j + 1 :]:
                yield (card1, card2, card3)


class State(Enum):

    IN_GAME = "in game"
    GAME_OVER = "game over"


class SetGame:
    def __init__(self):
        self.state = State.IN_GAME
        self._draw = set(
            Card(number=number, color=color, shading=shading, symbol=symbol)
            for number, color, shading, symbol in itertools.product(
                Number, Color, Shading, Symbol
            )
        )
        self._active = []
        self._discard = []

        self._deal(12)
        self._ensure_options()

    def _deal(self, n: int, replace_pos: Iterable = None):
        deal = random.sample(self._draw, n)
        if replace_pos is None:
            self._active.extend(deal)
        else:
            for pos, card in zip(replace_pos, deal):
                self._active.insert(pos, card)
        self._draw -= set(deal)

    def _ensure_options(self):
        while len(list(find_triples(self._active))) == 0:
            if len(self._draw) == 0:
                self.state = State.GAME_OVER
                return
            self._deal(3)

    @property
    def active_cards(self):
        return self._active

    @property
    def solved_sets(self):
        return self._discard

    @property
    def deck_remaining(self):
        return len(self._draw)

    def remove_set(self, a: Card, b: Card, c: Card):
        if self.state == State.GAME_OVER:
            raise ValueError("game is over")

        triple = {a, b, c}

        if len(triple) != 3:
            raise ValueError("cards are not unique")
        for card in triple:
            if card not in self._active:
                raise ValueError(f"{card} is not active")
        if a.complement(b) != c:
            raise ValueError("cards do not form a set")

        self._discard.append(triple)
        replace_pos = sorted((self._active.index(card) for card in triple))
        for pos in reversed(replace_pos):
            self._active.pop(pos)

        if len(self._draw) > 0 and len(self._active) < 12:
            self._deal(3, replace_pos)

        self._ensure_options()


if __name__ == "__main__":
    pygame.init()
    main()
