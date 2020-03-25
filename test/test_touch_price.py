import pytest
from shioaji.contracts import Future
from shioaji.order import Order
from touchprice import TouchOrder, TouchOrderCond


@pytest.fixture()
def api(mocker):
    api = mocker.MagicMock()
    return api


@pytest.fixture()
def touch_order(api):
    return TouchOrder(api)


@pytest.fixture()
def contract():
    return Future(
        code="TXFC0",
        symbol="TXF202003",
        name="臺股期貨",
        category="TXF",
        delivery_month="202003",
        underlying_kind="I",
    )


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


def test_set_condition(contract: Future, order: Order, touch_order: TouchOrder):
    condition = TouchOrderCond(order=order, contract=contract, touch_price=9985)
    touch_order.set_condition(condition)
    res = touch_order.conditions.get(condition.contract.code)
    assert res == condition
    touch_order.api.quote.subscribe.assert_called_once_with(condition.contract)


testcase_delete_condition = [["TXFC0", True], ["TXFD0", False]]


@pytest.mark.parametrize(
    "contract_code, unsubscribed", testcase_delete_condition
)
def test_delete_condition(
    contract: Future,
    order: Order,
    touch_order: TouchOrder,
    contract_code: str,
    unsubscribed: bool,
):
    touch_cond = TouchOrderCond(
        order=order, contract=contract, touch_price=9985
    )
    touch_order.conditions = {contract_code: touch_cond}
    touch_order.delete_condition(touch_cond)
    res = not touch_order.conditions
    assert res == unsubscribed
    assert touch_order.api.quote.unsubscribe.called == unsubscribed


testcase_touch = [[9985, True], [9999, False]]


@pytest.mark.parametrize("price, price_touched", testcase_touch)
def test_touch(
    contract: Future,
    order: Order,
    touch_order: TouchOrder,
    price: float,
    price_touched: bool,
):
    topic = "O/TXFC0"
    quote = {"Close": [9985]}
    touch_cond = TouchOrderCond(
        order=order, contract=contract, touch_price=price
    )
    touch_order.conditions = {touch_cond.contract.code: touch_cond}
    touch_order.touch(topic, quote)
    res = touch_order.conditions.get(touch_cond.contract.code).flag
    assert res == price_touched
    assert touch_order.api.place_order.called == price_touched
    assert touch_order.api.quote.unsubscribe.called == price_touched
    if price_touched:
        touch_order.api.place_order.assert_called_once_with(
            touch_cond.contract, touch_cond.order
        )
        touch_order.api.quote.unsubscribe.assert_called_once_with(
            touch_cond.contract
        )

