import shioaji as sj
from pydantic import BaseModel


class TouchOrderCond(BaseModel):
    contract: sj.contracts.Contract
    order: sj.order.Order
    touch_price: int
    flag: bool = False


class TouchOrder:
    def __init__(self, api: sj.Shioaji):
        self.api: sj.Shioaji = api
        self.conditions: dict = {}

    def set_condition(self, condition: TouchOrderCond):
        self.conditions.update({condition.contract.code: condition})
        self.api.quote.subscribe(condition.contract)
        self.api.quote.set_quote_callback(self.touch)
    
    def delete_condition(self, condition: TouchOrderCond):
        if self.conditions.get(condition.contract.code, False):
            self.conditions.pop(condition.contract.code)
            self.api.quote.unsubscribe(condition.contract)

    def touch(self, topic, quote):
        code = topic.split("/")[-1]
        price = quote["Close"][0]
        data = self.conditions.get(code, False)
        if data:
            if price == data.touch_price and not data.flag:
                self.api.place_order(data.contract, data.order)
                self.conditions[code].flag = True
                self.api.quote.unsubscribe(data.contract)