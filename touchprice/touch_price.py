import shioaji as sj
import typing
from pydantic import BaseModel


class TouchCmd(BaseModel):
    contract: sj.contracts.Contract
    price: float

    def __init__(self, contract: sj.contracts.Contract, price: float):
        super().__init__(**dict(contract=contract, price=price))


class OrderCmd(BaseModel):
    contract: sj.contracts.Contract
    order: sj.order.Order
    excuted: bool = False

    def __init__(
        self,
        contract: sj.contracts.Contract,
        order: sj.order.Order,
        excuted: bool = False,
    ):
        super().__init__(
            **dict(contract=contract, order=order, excuted=excuted)
        )


class TouchOrderCond(BaseModel):
    touch_cmd: TouchCmd
    order_cmd: OrderCmd

    def __init__(self, touch_cmd: TouchCmd, order_cmd: OrderCmd):
        super().__init__(**dict(touch_cmd=touch_cmd, order_cmd=order_cmd))


class TouchOrder:
    def __init__(self, api: sj.Shioaji):
        self.api: sj.Shioaji = api
        self.conditions: typing.Dict[str, typing.List[OrderCmd]] = {}

    def set_condition(self, condition: TouchOrderCond):
        condition_key = "{code}/{price}".format(
            code=condition.touch_cmd.contract.code,
            price=condition.touch_cmd.price,
        )
        order_condition = condition.order_cmd
        if condition_key in self.conditions.keys():
            self.conditions[condition_key].append(order_condition)
        else:
            self.conditions[condition_key] = [order_condition]
        self.api.quote.subscribe(condition.touch_cmd.contract)
        self.api.quote.set_quote_callback(self.touch)

    def delete_condition(self, condition: TouchOrderCond):
        condition_key = "{code}/{price}".format(
            code=condition.touch_cmd.contract.code,
            price=condition.touch_cmd.price,
        )
        order_cmd = condition.order_cmd
        if self.conditions.get(condition_key, False):
            if order_cmd in self.conditions[condition_key]:
                self.conditions[condition_key].remove(order_cmd)
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
                    self.conditions[touch_key][num].excuted = True
                    trade = self.api.place_order(cmd.contract, cmd.order)