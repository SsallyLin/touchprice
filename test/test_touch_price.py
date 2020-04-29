import pytest
import typing
from shioaji.contracts import Future
from shioaji.order import Order
from shioaji.data import Snapshots, Snapshot
from touchprice import (
    TouchOrder,
    TouchOrderCond,
    OrderCmd,
    TouchCmd,
    StoreCond,
    PriceGap,
    Price,
    PriceType,
    Trend,
    StatusInfo,
)


@pytest.fixture()
def api(mocker):
    api = mocker.MagicMock()
    return api


@pytest.fixture()
def touch_order(api):
    return TouchOrder(api)


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
    touch_order: TouchOrder, contract: Future, price_type: PriceType, excepted: float
):
    price_info = Price(price=9999.0, price_type=price_type, trend="Up")
    touch_order.contracts = contract
    res = touch_order.set_price(price_info, contract["TXFC0"])
    assert res.price == dict(contract["TXFC0"]).get(excepted, price_info.price)


testcase_update_snapshot = [["TXFD0", True], ["TXFC0", False]]


@pytest.mark.parametrize("code, in_infos", testcase_update_snapshot)
def test_update_snapshot(
    mocker,
    touch_order: TouchOrder,
    snapshot: Snapshot,
    contract: Future,
    code: str,
    in_infos: bool,
):
    touch_order.infos = {"TXFD0": snapshot}
    touch_order.api.snapshots = mocker.MagicMock(
        return_value=Snapshots(
            snapshot=[
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
    )
    touch_order.update_snapshot(contract["TXFC0"])
    if not in_infos:
        assert touch_order.api.snapshots.call_count == 1


testcase_adjust_condition = [
    [Price(price=3, trend="Up", price_type="LimitDown"), False],
    [None, True],
]


@pytest.mark.parametrize("condition, expected", testcase_adjust_condition)
def test_adjust_condition(
    mocker,
    touch_order: TouchOrder,
    contract: Future,
    order: Order,
    condition: Price,
    expected: bool,
):
    touchorder_cond = TouchOrderCond(
        touch_cmd=TouchCmd(code="TXFC0", close=condition),
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
def test_set_condition(
    mocker, contract: Future, order: Order, touch_order: TouchOrder, code: str
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
    touch_order.set_condition(condition)
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


testcase_delete_condition = [["TXFC0", 0], ["TXFD0", 1]]


@pytest.mark.parametrize("contract_code, condition_len", testcase_delete_condition)
def test_delete_condition(
    mocker,
    contract: Future,
    order: Order,
    touch_order: TouchOrder,
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
    touch_order: TouchOrder,
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


testcase_integration = [["MKT/2890", 1], ["QUT/2890", 1], ["XXX/XX", 0]]


@pytest.mark.parametrize("topic, touch_count", testcase_integration)
def test_integration(mocker, touch_order: TouchOrder, topic: str, touch_count: int):
    quote = {
        "Close": [12],
        "VolSum": [1],
        "Volume": [1],
        "BidPrice": [11],
        "AskPrice": [11],
    }
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
