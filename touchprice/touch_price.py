import shioaji as sj
import typing
from pydantic import BaseModel


class TouchCmd(BaseModel):
    code: str
    price: float

    def __init__(self, code: str, price: float):
        super().__init__(**dict(code=code, price=price))


class OrderCmd(BaseModel):
    code: str
    order: sj.order.Order

    def __init__(self, code: str, order: sj.order.Order):
        super().__init__(**dict(code=code, order=order))


class TouchOrderCond(BaseModel):
    touch_cmd: TouchCmd
    order_cmd: OrderCmd

    def __init__(self, touch_cmd: TouchCmd, order_cmd: OrderCmd):
        super().__init__(**dict(touch_cmd=touch_cmd, order_cmd=order_cmd))


class StoreCond(BaseModel):
    price: float
    action: str
    order_contract: sj.contracts.Contract
    order: sj.Order
    excuted: bool = False


def get_contracts(api: sj.Shioaji):
    contracts = {
        code: contract
        for name, iter_contract in api.Contracts
        for code, contract in iter_contract._code1contract.items()
    }
    return contracts


class TouchOrder:
    def __init__(self, api: sj.Shioaji):
        self.api: sj.Shioaji = api
        self.conditions: typing.Dict[str, typing.List[StoreCond]] = {}
        self.contracts: dict = get_contracts(self.api)

    def set_condition(self, condition: TouchOrderCond):
        code = condition.touch_cmd.code
        touch_contract = self.contracts[code]
        store_condition = StoreCond(price=condition.touch_cmd.price,
                                    action=condition.order_cmd.order.action,
                                    order_contract=self.contracts[
                                        condition.order_cmd.code],
                                    order=condition.order_cmd.order)
        if code in self.conditions.keys():
            self.conditions[code].append(store_condition)
        else:
            self.conditions[code] = [store_condition]
        self.api.quote.subscribe(touch_contract)
        self.api.quote.set_quote_callback(self.touch)

    def delete_condition(self, condition: TouchOrderCond):
        code = condition.touch_cmd.code
        store_condition = StoreCond(price=condition.touch_cmd.price,
                                    action=condition.order_cmd.order.action,
                                    order_contract=self.contracts[
                                        condition.order_cmd.code],
                                    order=condition.order_cmd.order)
        if self.conditions.get(code, False):
            if store_condition in self.conditions[code]:
                self.conditions[code].remove(store_condition)
                return self.conditions[code]


    def touch(self, topic, quote):
        code = topic.split("/")[-1]
        price = quote["Close"][0]
        ordercmds = self.conditions.get(code, False)
        if ordercmds:
            for num, cmd in enumerate(ordercmds):
                if not cmd.excuted:
                    if cmd.action == "Buy":
                        if price >= cmd.price:
                            self.conditions[code][num].excuted = True
                            trade = self.api.place_order(cmd.order_contract, cmd.order)
                    else:
                        if price <= cmd.price:
                            self.conditions[code][num].excuted = True
                            trade = self.api.place_order(cmd.order_contract, cmd.order)