from enum import Enum


class Trend(str, Enum):
    Up = "Up"
    Down = "Down"
    Equal = "Equal"


class PriceType(str, Enum):
    LimitPrice = "LimitPrice"  # 限價
    LimitUp = "LimitUp"  # 漲停
    Unchanged = "Unchanged"  # 平盤
    LimitDown = "LimitDown"  # 跌停
