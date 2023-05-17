import pytest
import typing
import datetime
from decimal import Decimal
from dataclasses import dataclass
from shioaji.account import StockAccount, Account
from shioaji.contracts import Future, Stock, Contract
from shioaji.order import Order, Trade, OrderStatus
from shioaji.data import Snapshot
from shioaji import Exchange
from touchprice import (
    TouchOrderExecutor,
    TouchOrderCond,
    OrderCmd,
    TouchCmd,
    StoreCond,
    PriceGap,
    Price,
    PriceType,
    Trend,
    StatusInfo,
    Qty,
    QtyGap,
    StoreLossProfit,
)


@dataclass
class BidAskSTKv1:
    code: str
    bid_price: typing.List[Decimal]
    bid_volume: typing.List[int]
    ask_price: typing.List[Decimal]
    ask_volume: typing.List[int]
    simtrade: bool


@dataclass
class TickSTKv1:
    code: str
    close: Decimal
    high: Decimal
    low: Decimal
    amount: Decimal
    total_amount: Decimal
    volume: int
    total_volume: int
    tick_type: int
    simtrade: bool


@pytest.fixture()
def api(mocker):
    api = mocker.MagicMock()
    return api


@pytest.fixture()
def touch_order(api):
    return TouchOrderExecutor(api)


@pytest.fixture()
def contract():
    return {
        "TXFC0": Future(
            code="TXFC0",
            symbol="TXF202003",
            name="臺股期貨",
            category="TXF",
            delivery_month="202003",
            underlying_kind="I",
            limit_up=10805.0,
            limit_down=8841.0,
            reference=9823.0,
            update_date="2020/04/07",
        )
    }


@pytest.fixture()
def order():
    return Order(
        action="Buy",
        price=-1,
        quantity=1,
        order_type="ROD",
        price_type="MKT",
        octype="Auto",
    )


@pytest.fixture()
def snapshot():
    return Snapshot(
        ts=1586957400087000000,
        code="TXFD0",
        exchange="TAIFEX",
        open=10347.0,
        high=10463.0,
        low=10330.0,
        close=10450.0,
        tick_type="Sell",
        change_price=107.0,
        change_rate=1.03,
        change_type="Up",
        average_price=10410.18,
        volume=3,
        total_volume=65128,
        amount=31350,
        total_amount=677994228,
        yesterday_volume=27842.0,
        buy_price=10450.0,
        buy_volume=1710.0,
        sell_price=10451.0,
        sell_volume=9,
        volume_ratio=2.34,
    )


testcase_set_price = [
    ["LimitDown", "limit_down"],
    ["LimitUp", "limit_up"],
    ["LimitPrice", ""],
    ["Unchanged", "reference"],
]


@pytest.mark.parametrize("price_type, excepted", testcase_set_price)
def test_set_price(
    touch_order: TouchOrderExecutor,
    contract: Future,
    price_type: PriceType,
    excepted: float,
):
    price_info = Price(price=9999.0, price_type=price_type, trend="Up")
    touch_order.contracts = contract
    res = touch_order.set_price(price_info, contract["TXFC0"])
    assert res.price == dict(contract["TXFC0"]).get(excepted, price_info.price)


testcase_update_snapshot = [["TXFD0", True], ["TXFC0", False]]


@pytest.mark.parametrize("code, in_infos", testcase_update_snapshot)
def test_update_snapshot(
    mocker,
    touch_order: TouchOrderExecutor,
    snapshot: Snapshot,
    contract: Future,
    code: str,
    in_infos: bool,
):
    touch_order.infos = {"TXFD0": snapshot}
    touch_order.api.snapshots = mocker.MagicMock(
        return_value=[
            Snapshot(
                ts=1586957400087000000,
                code="TXFD0",
                exchange="TAIFEX",
                open=10347.0,
                high=10463.0,
                low=10330.0,
                close=10450.0,
                tick_type="Sell",
                change_price=107.0,
                change_rate=1.03,
                change_type="Up",
                average_price=10410.18,
                volume=3,
                total_volume=65128,
                amount=31350,
                total_amount=677994228,
                yesterday_volume=27842.0,
                buy_price=10450.0,
                buy_volume=1710.0,
                sell_price=10451.0,
                sell_volume=9,
                volume_ratio=2.34,
            )
        ]
    )
    touch_order.update_snapshot(contract["TXFC0"])
    if not in_infos:
        assert touch_order.api.snapshots.call_count == 1


testcase_adjust_condition = [
    [
        TouchCmd(
            code="TXFC0", close=Price(price=3, trend="Up", price_type="LimitDown")
        ),
        False,
    ],
    [TouchCmd(code="TXFC0", volume=Qty(qty=3)), False],
    [TouchCmd(code="TXFC0"), True],
]


@pytest.mark.parametrize("touch_cmd, expected", testcase_adjust_condition)
def test_adjust_condition(
    mocker,
    touch_order: TouchOrderExecutor,
    contract: Future,
    order: Order,
    touch_cmd: TouchCmd,
    expected: bool,
):
    touchorder_cond = TouchOrderCond(
        touch_cmd=touch_cmd,
        order_cmd=OrderCmd(code="TXFC0", order=order),
    )
    touch_order.contracts = contract
    contract = touch_order.contracts["TXFC0"]
    touch_order.set_price = mocker.MagicMock(
        return_value=PriceGap(price=10, trend="Up")
    )
    res = touch_order.adjust_condition(touchorder_cond, contract) is None
    assert res == expected


testcase_set_condition = ["TXFC0", "TXFD0"]


@pytest.mark.parametrize("code", testcase_set_condition)
def test_add_condition(
    mocker, contract: Future, order: Order, touch_order: TouchOrderExecutor, code: str
):
    touch_order.contracts = {"TXFC0": contract["TXFC0"], "TXFD0": contract["TXFC0"]}
    store_cond = StoreCond(
        close=PriceGap(price=10, trend="Up"),
        order_contract=touch_order.contracts["TXFC0"],
        order=order,
    )
    condition = TouchOrderCond(
        touch_cmd=TouchCmd(code=code, close=Price(price=10, trend="Up")),
        order_cmd=OrderCmd(code="TXFC0", order=order),
    )
    touch_order.conditions = {"TXFC0": [store_cond]}
    touch_order.update_snapshot = mocker.MagicMock()
    touch_order.adjust_condition = mocker.MagicMock()
    touch_order.add_condition(condition)
    touch_order.update_snapshot.assert_called_once_with(
        touch_order.contracts[condition.touch_cmd.code]
    )
    touch_order.adjust_condition.assert_called_with(
        condition, touch_order.contracts[condition.touch_cmd.code]
    )
    touch_order.api.quote.subscribe.assert_called_with(
        touch_order.contracts[condition.touch_cmd.code], quote_type="bidask"
    )
    assert touch_order.api.quote.subscribe.call_count == 2
    res = touch_order.conditions.get(condition.touch_cmd.code)
    assert not res == False


testcase_touch_cond = [
    [{"price": 11, "trend": "Up"}, 10, None],
    [{"price": 11, "trend": "Up"}, 11, True],
    [{"price": 11, "trend": "Up"}, 12, True],
    [{"price": 11, "trend": "Down"}, 10, True],
    [{"price": 11, "trend": "Down"}, 11, True],
    [{"price": 11, "trend": "Down"}, 12, None],
    [{"price": 11, "trend": "Equal"}, 11, True],
    [{"price": 11, "trend": "Equal"}, 10, None],
    [{"ask_volume": 11, "trend": "Equal"}, 11, True],
    [{"ask_volume": 11, "trend": "Equal"}, 10, None],
    [{"ask_volume": 11, "trend": "Up"}, 12, True],
]


@pytest.mark.parametrize("info, value, expected", testcase_touch_cond)
def test_touch_cond(
    info: typing.Dict,
    value: float,
    expected: bool,
    touch_order: TouchOrderExecutor,
):
    res = touch_order.touch_cond(info, value)
    assert res == expected


testcase_delete_condition = [["TXFC0", 0], ["TXFD0", 1]]


@pytest.mark.parametrize("contract_code, condition_len", testcase_delete_condition)
def test_delete_condition(
    mocker,
    contract: Future,
    order: Order,
    touch_order: TouchOrderExecutor,
    contract_code: str,
    condition_len: int,
):
    touch_order.contracts = contract
    touch_cond = TouchOrderCond(
        touch_cmd=TouchCmd(
            code="TXFC0",
            close=PriceGap(price=11.0, price_type="LimitPrice", trend="Up"),
        ),
        order_cmd=OrderCmd(code="TXFC0", order=order),
    )
    touch_order.conditions = {
        contract_code: [
            StoreCond(
                price=PriceGap(price=11.0, trend="Up"),
                order_contract=touch_order.contracts["TXFC0"],
                order=touch_cond.order_cmd.order,
                excuted=False,
            )
        ]
    }
    touch_order.adjust_condition = mocker.MagicMock(
        return_value=touch_order.conditions[contract_code][0]
    )
    touch_order.delete_condition(touch_cond)
    assert len(touch_order.conditions[contract_code]) == condition_len


testcase_touch = [
    ["TXFC0", PriceGap(price=9900, price_type="LimitPrice", trend="Up"), 0, 0],
    ["TXFD0", PriceGap(price=9985, price_type="LimitPrice", trend="Up"), 9986, 1],
    ["TXFD0", PriceGap(price=9985, price_type="LimitPrice", trend="Up"), 9980, 0],
]


@pytest.mark.parametrize("code, price, close_price, order_count", testcase_touch)
def test_touch_storecond(
    mocker,
    contract: Future,
    order: Order,
    touch_order: TouchOrderExecutor,
    code: str,
    price: PriceGap,
    close_price: float,
    order_count: int,
):
    touch_order.conditions = {
        "TXFD0": [
            StoreCond(
                close=price,
                order_contract=contract["TXFC0"],
                order=order,
                excuted=False,
            )
        ]
    }
    touch_order.infos["TXFD0"] = StatusInfo(
        close=close_price,
        buy_price=11,
        sell_price=11,
        high=11,
        low=11,
        change_price=11,
        change_rate=1,
        volume=1,
        total_volume=1,
    )
    touch_order.touch(code)
    assert touch_order.api.place_order.call_count == order_count


testcase_touch_profit = [
    [
        "TXFD0",
        PriceGap(price=9900, price_type="LimitPrice", trend="Down"),
        None,
        9900,
        1,
    ],
    [
        "TXFD0",
        PriceGap(price=9900, price_type="LimitPrice", trend="Down"),
        None,
        9800,
        1,
    ],
    [
        "TXFD0",
        PriceGap(price=9900, price_type="LimitPrice", trend="Down"),
        None,
        9901,
        0,
    ],
    ["TXFD0", None, PriceGap(price=9900, price_type="LimitPrice", trend="Up"), 9900, 1],
    ["TXFD0", None, PriceGap(price=9900, price_type="LimitPrice", trend="Up"), 9901, 1],
    ["TXFD0", None, PriceGap(price=9900, price_type="LimitPrice", trend="Up"), 9800, 0],
    [
        "TXFD0",
        PriceGap(price=9800, price_type="LimitPrice", trend="Down"),
        PriceGap(price=10000, price_type="LimitPrice", trend="Up"),
        9900,
        0,
    ],
    [
        "TXFD0",
        PriceGap(price=9900, price_type="LimitPrice", trend="Down"),
        PriceGap(price=10000, price_type="LimitPrice", trend="Up"),
        9900,
        1,
    ],
    [
        "TXFD0",
        PriceGap(price=9800, price_type="LimitPrice", trend="Down"),
        PriceGap(price=9900, price_type="LimitPrice", trend="Up"),
        9900,
        1,
    ],
]


@pytest.mark.parametrize(
    "code, loss_close, profit_close, close_price, order_count", testcase_touch_profit
)
def test_touch_storelossprofit(
    mocker,
    loss_close: PriceGap,
    profit_close: PriceGap,
    contract: contract,
    order: Order,
    close_price: int,
    code: str,
    order_count: int,
    touch_order: TouchOrderExecutor,
):
    touch_order.conditions = {
        "TXFD0": [
            StoreLossProfit(
                loss_close=loss_close,
                profit_close=profit_close,
                order_contract=contract["TXFC0"],
                loss_order=order,
                profit_order=order,
                excuted=False,
            )
        ]
    }
    touch_order.infos["TXFD0"] = StatusInfo(
        close=close_price,
        buy_price=11,
        sell_price=11,
        high=11,
        low=11,
        change_price=11,
        change_rate=1,
        volume=1,
        total_volume=1,
    )
    touch_order.touch(code)
    assert touch_order.api.place_order.call_count == order_count


testcase_integration_tick = [
    [
        Exchange.TSE,
        TickSTKv1(
            "2890",
            Decimal("590"),
            Decimal("593"),
            Decimal("587"),
            Decimal("590000"),
            Decimal("8540101000"),
            1,
            14498,
            1,
            1,
        ),
        0,
        7,
        0,
    ],
    [
        Exchange.TSE,
        TickSTKv1(
            "2890",
            Decimal("590"),
            Decimal("593"),
            Decimal("587"),
            Decimal("590000"),
            Decimal("8540101000"),
            1,
            14498,
            1,
            0,
        ),
        1,
        8,
        0,
    ],
    [
        Exchange.TSE,
        TickSTKv1(
            "2890",
            Decimal("590"),
            Decimal("593"),
            Decimal("587"),
            Decimal("590000"),
            Decimal("8540101000"),
            1,
            14498,
            2,
            0,
        ),
        1,
        0,
        1,
    ],
    [
        Exchange.TSE,
        TickSTKv1(
            "1234",
            Decimal("590"),
            Decimal("593"),
            Decimal("587"),
            Decimal("590000"),
            Decimal("8540101000"),
            1,
            14498,
            1,
            0,
        ),
        0,
        7,
        0,
    ],
]


@pytest.mark.parametrize(
    "exchange, tick, touch_count, ask_volume, bid_volume", testcase_integration_tick
)
def test_integration_tick(
    mocker,
    touch_order: TouchOrderExecutor,
    exchange: Exchange,
    tick: TickSTKv1,
    touch_count: int,
    ask_volume: int,
    bid_volume: int,
):
    touch_order.infos = {
        "2890": StatusInfo(
            close=11,
            buy_price=11,
            sell_price=11,
            high=11,
            low=11,
            change_price=1,
            change_rate=1.0,
            volume=1,
            total_volume=10,
            ask_volume=7,
            bid_volume=0,
        )
    }
    touch_order.touch = mocker.MagicMock()
    touch_order.integration_tick(exchange, tick)
    assert touch_order.touch.call_count == touch_count
    assert touch_order.infos["2890"].ask_volume == ask_volume
    assert touch_order.infos["2890"].bid_volume == bid_volume


testcase_integration_bidask = [
    [
        Exchange.TSE,
        BidAskSTKv1(
            "2890",
            [
                Decimal("589"),
                Decimal("588"),
                Decimal("587"),
                Decimal("586"),
                Decimal("585"),
            ],
            [59391, 224490, 74082, 68570, 125246],
            [
                Decimal("590"),
                Decimal("591"),
                Decimal("592"),
                Decimal("593"),
                Decimal("594"),
            ],
            [26355, 9680, 18087, 11773, 3568],
            0,
        ),
        1,
        7,
        0,
    ],
    [
        Exchange.TSE,
        BidAskSTKv1(
            "2890",
            [
                Decimal("0"),
                Decimal("0"),
                Decimal("0"),
                Decimal("0"),
                Decimal("0"),
            ],
            [0, 0, 0, 0, 0],
            [
                Decimal("0"),
                Decimal("0"),
                Decimal("0"),
                Decimal("0"),
                Decimal("0"),
            ],
            [0, 0, 0, 0, 0],
            1,
        ),
        0,
        7,
        0,
    ],
    [
        Exchange.TSE,
        BidAskSTKv1(
            "2330",
            [
                Decimal("589"),
                Decimal("588"),
                Decimal("587"),
                Decimal("586"),
                Decimal("585"),
            ],
            [939, 224490, 74082, 68570, 125246],
            [
                Decimal("590"),
                Decimal("591"),
                Decimal("592"),
                Decimal("593"),
                Decimal("594"),
            ],
            [26355, 9680, 18087, 11773, 3568],
            1,
        ),
        0,
        7,
        0,
    ],
]


@pytest.mark.parametrize(
    "exchange, bidask, touch_count, ask_volume, bid_volume", testcase_integration_bidask
)
def test_integration_bidask(
    mocker,
    touch_order: TouchOrderExecutor,
    exchange: Exchange,
    bidask: BidAskSTKv1,
    touch_count: int,
    ask_volume: int,
    bid_volume: int,
):
    touch_order.infos = {
        "2890": StatusInfo(
            close=11,
            buy_price=11,
            sell_price=11,
            high=11,
            low=11,
            change_price=1,
            change_rate=1.0,
            volume=1,
            total_volume=10,
            ask_volume=7,
            bid_volume=0,
        )
    }
    touch_order.touch = mocker.MagicMock()
    touch_order.integration_bidask(exchange, bidask)
    assert touch_order.touch.call_count == touch_count
    assert touch_order.infos["2890"].ask_volume == ask_volume
    assert touch_order.infos["2890"].bid_volume == bid_volume


testcase_show_condition = [["", 2], ["TXFC0", 1]]


@pytest.mark.parametrize("code, length", testcase_show_condition)
def test_show_condition(
    contract: Future,
    order: Order,
    code: str,
    length: int,
    touch_order: TouchOrderExecutor,
):
    touch_order.conditions = {
        "TXFC0": [
            StoreCond(
                close=PriceGap(price=9928, trend="Up"),
                order_contract=contract["TXFC0"],
                order=order,
            )
        ],
        "TXFD0": [
            StoreCond(
                close=PriceGap(price=9928, trend="Up"),
                order_contract=contract["TXFC0"],
                order=order,
            )
        ],
    }
    res = len(touch_order.show_condition(code))
    assert res == length
