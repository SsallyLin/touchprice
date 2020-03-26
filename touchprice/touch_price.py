import shioaji as sj
import typing
from pydantic import BaseModel


class OrderCmd(BaseModel):
    contract: sj.contracts.Contract
    order: sj.order.Order
    excuted: bool = False


class TouchOrderCond(BaseModel):
    touch_contract: sj.contracts.Contract
    touch_price: float
    order_cmd: OrderCmd


class TouchOrder:
    def __init__(self, api: sj.Shioaji):
        self.api: sj.Shioaji = api
        self.conditions: typing.Dict[str, typing.List[OrderCmd]] = {}

    def set_condition(self, condition: TouchOrderCond):
        condition_key = "{code}/{price}".format(
            code=condition.touch_contract.code, price=condition.touch_price
        )
        order_condition = OrderCmd(
            contract=condition.order_cmd.contract,
            order=condition.order_cmd.order,
        )
        if condition_key in self.conditions.keys():
            self.conditions[condition_key].append(order_condition)
        else:
            self.conditions[condition_key] = [order_condition]
        self.api.quote.subscribe(condition.touch_contract)
        self.api.quote.set_quote_callback(self.touch)

    def delete_condition(self, condition: TouchOrderCond):
        condition_key = "{code}/{price}".format(
            code=condition.touch_contract.code, price=condition.touch_price
        )
        if self.conditions.get(condition_key, False):
            ordercmd = OrderCmd(
                contract=condition.order_cmd.contract,
                order=condition.order_cmd.order,
                excuted=condition.order_cmd.excuted,
            )
            self.conditions[condition_key].remove(ordercmd)
            return self.conditions[condition_key]

    def show_condition(self, touch_code: str = None, touch_price: float = None):
        if touch_code and touch_price:
            cond_key = "{}/{}".format(touch_code, touch_price)
            return self.conditions.get(cond_key, "Not exist.")
        else:
            return self.conditions

    def touch(self, topic, quote):
        code = topic.split("/")[-1]
        price = quote["Close"][0]
        touch_key = "{code}/{price}".format(code=code, price=price)
        ordercmds = self.conditions.get(touch_key, False)
        if ordercmds:
            for num, cmd in enumerate(ordercmds):
                if not cmd.excuted:
                    trade = self.api.place_order(cmd.contract, cmd.order)
                    if trade.status.status != sj.order.Status.Failed:
                        self.conditions[touch_key][num].excuted = True
