import pytest
import typing
from shioaji.contracts import Future
from shioaji.order import Order
from shioaji.data import Snapshot
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
)


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
        touch_cmd=touch_cmd, order_cmd=OrderCmd(code="TXFC0", order=order),
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
]


@pytest.mark.parametrize("info, value, expected", testcase_touch_cond)
def test_touch_cond(
    info: typing.Dict, value: float, expected: bool, touch_order: TouchOrderExecutor,
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
def test_touch(
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


testcase_integration = [
    [
        "MKT/2890",
        {
            "AmountSum": [4869957500.0],
            "Close": [297.5],
            "Date": "2020/05/21",
            "TickType": [1],
            "Time": "10:46:27.610865",
            "VolSum": [16415],
            "Volume": [1],
            "Simtrade": 1,
        },
        0,
    ],
    [
        "MKT/2890",
        {
            "AmountSum": [4869957500.0],
            "Close": [297.5],
            "Date": "2020/05/21",
            "TickType": [1],
            "Time": "10:46:27.610865",
            "VolSum": [16415],
            "Volume": [1],
        },
        1,
    ],
    [
        "QUT/2890",
        {
            "AskPrice": [11.75, 11.8, 11.85, 11.9, 11.95],
            "AskVolume": [853, 1269, 1049, 730, 198],
            "BidPrice": [11.7, 11.65, 11.6, 11.55, 11.5],
            "BidVolume": [534, 1331, 1146, 990, 2423],
            "Date": "2020/05/21",
            "Time": "09:46:01.835229",
        },
        1,
    ],
    [
        "QUT/2890",
        {
            "AskPrice": [0, 0, 0, 0, 0],
            "AskVolume": [0, 0, 0, 0, 0],
            "BidPrice": [0, 0, 0, 0, 0],
            "BidVolume": [0, 0, 0, 0, 0],
            "Date": "2020/05/21",
            "Time": "09:46:01.835229",
        },
        0,
    ],
    [
        "XXX/XX",
        {
            "Close": [12],
            "VolSum": [1],
            "Volume": [1],
            "BidPrice": [11],
            "AskPrice": [11],
        },
        0,
    ],
]


@pytest.mark.parametrize("topic, quote, touch_count", testcase_integration)
def test_integration(
    mocker,
    touch_order: TouchOrderExecutor,
    topic: str,
    quote: typing.Dict,
    touch_count: int,
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
        )
    }
    touch_order.touch = mocker.MagicMock()
    touch_order.integration(topic, quote)
    assert touch_order.touch.call_count == touch_count


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
