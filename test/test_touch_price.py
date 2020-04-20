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
    Scope,
    QtyGap,
    Qty,
    PriceType,
    ScopeType,
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


# test_condition = [
#     [TouchCond(price=PriceInterval(price_type="LimitUp"))],
#     [TouchCond(buy_price=PriceInterval(price=11.0, price_type="LimitDown"))],
#     [TouchCond(low_price=PriceInterval(price_type="LimitPrice"))],
#     [TouchCond(ups_downs=Scope(scope=3, scopetype="UpAbove"))],
#     [TouchCond(scope=Scope(scope=3, scopetype="DownBelow"))],
#     [TouchCond(qty=QtyInterval(qty=2, trend="Up"))],
#     [
#         TouchCond(
#             price=PriceInterval(price_type="Unchanged"),
#             ups_downs=Scope(scope=7, scopetype="UpBelow"),
#         )
#     ],
#     [
#         TouchCond(
#             buy_price=PriceInterval(price=10.0, price_type="LimitPrice"),
#             qty=QtyInterval(qty=1, trend="Down"),
#         )
#     ],
#     [
#         TouchCond(
#             scope=Scope(scope=3.5, scopetype="DownAbove"),
#             qty=QtyInterval(qty=5, trend="Equal"),
#         )
#     ],
#     [
#         TouchCond(
#             low_price=PriceInterval(price_type="Unchanged"),
#             ups_downs=Scope(scope=3, scopetype="UpAbove"),
#             sum_qty=QtyInterval(qty=100, trend="Up"),
#         )
#     ],
#     [TouchCond()],
# ]

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


testcase_scope2price = [
    [3, "UpAbove", "ups_downs", 9826.0, "Up"],
    [0.03, "DownBelow", "scope", 9528.31, "Down"],
]


@pytest.mark.parametrize(
    "scope, scope_type, info_name, price, trend", testcase_scope2price
)
def test_scope2price(
    touch_order: TouchOrder,
    contract: Future,
    scope: typing.Union[int, float],
    scope_type: str,
    info_name: str,
    price: float,
    trend: str,
):
    scope_info = Scope(scope=scope, scope_type=scope_type)
    res = touch_order.scope2price(scope_info, info_name, contract["TXFC0"])
    assert res.price == price
    assert res.trend == trend


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
    [
        TouchCond(
            price=Price(price=3, trend="Up"), buy_price=Price(price=3, trend="Up")
        ),
        2,
        0,
    ],
    [TouchCond(scope=Scope(scope=3, scope_type="UpAbove")), 0, 1],
    [TouchCond(qty=Qty(qty=2, trend="Up")), 0, 0],
    [
        TouchCond(
            price=Price(price=3, trend="Up"), scope=Scope(scope=3, scope_type="UpAbove")
        ),
        1,
        1,
    ],
    [
        TouchCond(
            price=Price(price=3, trend="Up"),
            scope=Scope(scope=3, scope_type="UpAbove"),
            qty=Qty(qty=2, trend="Up"),
        ),
        1,
        1,
    ],
    [
        TouchCond(
            scope=Scope(scope=3, scope_type="UpAbove"), qty=Qty(qty=2, trend="Up")
        ),
        0,
        1,
    ],
    [TouchCond(), 0, 0],
]


@pytest.mark.parametrize(
    "condition, price_counts, scope_counts", testcase_adjust_condition
)
def test_adjust_codition(
    mocker,
    touch_order: TouchOrder,
    contract: Future,
    order: Order,
    condition: TouchCond,
    price_counts: int,
    scope_counts: int,
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
    touch_order.scope2price = mocker.MagicMock(
        return_value=PriceGap(price=10, trend="Up")
    )
    touch_order.adjust_codition(touchorder_cond, contract)
    assert touch_order.set_price.call_count == price_counts
    assert touch_order.scope2price.call_count == scope_counts


def test_set_condition(mocker, contract: Future, order: Order, touch_order: TouchOrder):
    condition = TouchOrderCond(
        touch_cmd=TouchCmd(
            code="TXFC0",
            conditions=TouchCond(
                price=PriceInterval(price=11.0, price_type="LimitPrice", trend="Up")
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
        condition, touch_order.contracts[condition.touch_cmd.code]
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
        touch_cmd=TouchCmd(code="TXFC0", price=9985.0),
        order_cmd=OrderCmd(code="TXFC0", order=order),
    )
    cond_key = touch_cond.touch_cmd.code
    touch_order.contracts = contract
    touch_order.conditions = {
        contract_code: [
            StoreCond(
                price=touch_cond.touch_cmd.price,
                action=touch_cond.order_cmd.order.action,
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


testcase_touch = [[9900, True], [9985, True], [9999, False]]


@pytest.mark.parametrize("price, price_touched", testcase_touch)
def test_touch(
    contract: Future,
    order: Order,
    touch_order: TouchOrder,
    price: float,
    price_touched: bool,
):
    topic = "O/TXFC0"
    quote = {"Close": [9985.0]}
    touch_cond = TouchOrderCond(
        touch_cmd=TouchCmd(code="TXFC0", price=price),
        order_cmd=OrderCmd(code="TXFC0", order=order),
    )
    touch_key = touch_cond.touch_cmd.code
    touch_order.contracts = contract
    touch_order.conditions = {
        touch_key: [
            StoreCond(
                price=touch_cond.touch_cmd.price,
                action=touch_cond.order_cmd.order.action,
                order_contract=touch_order.contracts[touch_key],
                order=touch_cond.order_cmd.order,
                excuted=False,
            )
        ]
    }
    touch_order.touch(topic, quote)
    res = touch_order.conditions.get(touch_key)[-1].excuted
    assert res == price_touched
    assert touch_order.api.place_order.called == price_touched
    if price_touched:
        touch_order.api.place_order.assert_called_once_with(
            touch_order.conditions[touch_key][-1].order_contract,
            touch_order.conditions[touch_key][-1].order,
        )
