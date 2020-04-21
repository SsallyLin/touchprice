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
    TouchCond,
    StoreCond,
    PriceGap,
    Price,
    PriceType,
    Trend,
    StatusInfo,
    PriceTouchCond,
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
    [TouchCond(price=Price(price=3, trend="Up")), 1],
    [TouchCond(), 0],
]


@pytest.mark.parametrize("condition, count", testcase_adjust_condition)
def test_adjust_codition(
    mocker,
    touch_order: TouchOrder,
    contract: Future,
    order: Order,
    condition: TouchCond,
    count: int,
):
    touchorder_cond = TouchOrderCond(
        touch_cmd=TouchCmd(code="TXFC0", conditions=condition),
        order_cmd=OrderCmd(code="TXFC0", order=order),
    )
    touch_order.contracts = contract
    contract = touch_order.contracts["TXFC0"]
    touch_order.set_price = mocker.MagicMock(
        return_value=PriceGap(price=10, trend="Up")
    )
    touch_order.adjust_codition(touchorder_cond, contract)
    assert touch_order.set_price.call_count == count


def test_set_condition(mocker, contract: Future, order: Order, touch_order: TouchOrder):
    condition = TouchOrderCond(
        touch_cmd=TouchCmd(
            code="TXFC0",
            conditions=TouchCond(
                price=PriceGap(price=11.0, price_type="LimitPrice", trend="Up")
            ),
        ),
        order_cmd=OrderCmd(code="TXFC0", order=order),
    )
    touch_order.contracts = contract
    touch_order.update_snapshot = mocker.MagicMock()
    touch_order.adjust_codition = mocker.MagicMock()
    touch_order.set_condition(condition)
    touch_order.update_snapshot.assert_called_once_with(
        touch_order.contracts[condition.touch_cmd.code]
    )
    touch_order.adjust_codition.assert_called_with(
        condition.touch_cmd.conditions, touch_order.contracts[condition.touch_cmd.code]
    )
    touch_order.api.quote.subscribe.assert_called_with(
        touch_order.contracts[condition.touch_cmd.code], quote_type="bidask"
    )
    assert touch_order.api.quote.subscribe.call_count == 2
    res = touch_order.conditions.get(condition.touch_cmd.code)
    assert not res == False


testcase_delete_condition = [["TXFC0", False], ["TXFD0", False]]


@pytest.mark.parametrize("contract_code, deleted", testcase_delete_condition)
def test_delete_condition(
    contract: Future,
    order: Order,
    touch_order: TouchOrder,
    contract_code: str,
    deleted: bool,
):
    touch_cond = TouchOrderCond(
        touch_cmd=TouchCmd(
            code="TXFC0",
            conditions=TouchCond(
                price=PriceGap(price=11.0, price_type="LimitPrice", trend="Up")
            ),
        ),
        order_cmd=OrderCmd(code="TXFC0", order=order),
    )
    cond_key = touch_cond.touch_cmd.code
    touch_order.contracts = contract
    touch_order.conditions = {
        contract_code: [
            StoreCond(
                price_conditions=PriceTouchCond(price=PriceGap(price=1.0, trend="Up")),
                order_contract=touch_order.contracts[cond_key],
                order=touch_cond.order_cmd.order,
                excuted=False,
            )
        ]
    }
    touch_order.delete_condition(touch_cond)
    storecode = StoreCond(
        price=touch_cond.touch_cmd.price,
        action=touch_cond.order_cmd.order.action,
        order_contract=contract[touch_cond.order_cmd.code],
        order=touch_cond.order_cmd.order,
        excuted=False,
    )
    if touch_order.conditions.get(cond_key, False):
        res = storecode in touch_order.conditions.get(cond_key)
    else:
        res = False
    assert res == deleted


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
                price_conditions=PriceTouchCond(price=price),
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

