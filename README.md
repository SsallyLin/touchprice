# Shioaji touch order extension

[![PyPI - Status](https://img.shields.io/pypi/v/touchprice.svg?)](https://pypi.org/project/touchprice)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/touchprice.svg)]()
[![PyPI - Downloads](https://img.shields.io/pypi/dm/touchprice.svg?)](https://pypi.org/project/touchprice)
[![codecov](https://codecov.io/gh/SsallyLin/touchprice/branch/master/graph/badge.svg)](https://codecov.io/gh/SsallyLin/touchprice)
[![Build - Status](https://img.shields.io/github/workflow/status/SsallyLin/touchprice/Deploy)]()


Touchprice is an extension feature of Shioaji. Using the conditions to trigger placing order.

## Installation

    pip install touchprice

## Quickstarts
Just import our API library like other popular python library and adding Shioaji to start using the feature of touchprice.
``` 
import touchprice as tp
import shioaji as sj

api = sj.Shioaji()
api.login(USERID, PASSWORD)
api.activate_ca(CA_PATH, CA_USERID, CA_PASSWORD)
touch = tp.TouchOrder(api)
```   
## Condition
TouchOrderCond contains touch condition and order condition. 

### Set touch condition
```
touch_cmd = 
    tp.TouchCmd(
        code="2890", 
        close = tp.Price(price=11.0, trend="Up")
    )
```
#### TouchCmd arg:
* code: str,
* close: condition.Price = None,
* buy_price: condition.Price = None,
* sell_price: condition.Price = None,
* high: condition.Price = None,
* low: condition.Price = None,
* volume: condition.Qty = None,
* total_volume: condition.Qty = None,
* ask_volume: condition.Qty = None,
* bid_volume: condition.Qty = None,



#### Price arg
* price: float = 0.0,
* trend: constant.Trend = 'Equal' ('Up', 'Down', 'Equal')
* price_type: constant.PriceType = 'LimitPrice'  ('LimitPrice', 'LimitUp', 'Unchanged', 'LimitDown ')

#### Qty arg
* qty: int,
* trend: constant.Trend = 'Equal' ('Up', 'Down', 'Equal')




### Set order condition
```
order_cmd = tp.OrderCmd(
    code="2890",
    order = sj.Order(
        action="Buy",
        price=10,
        quantity=1,
        order_type="ROD",
        price_type="LMT",
    )

```
### OrderCmd arg
* code: str
* order: shioaji.order.Order




## Add condition to order    
```
condition = tp.TouchOrderCond(
                touch_cmd = touch_cond, 
                order_cmd = order_cond
            )
touch.add_condition(condition)
``` 
    

## Delete condition
    touch.delete_condition(condition)

## Show condition
If not set code can show all conditions, else just show coditions of code. 
``` 
touch.show_condition(code)
```

# Disclaimer
The package are used at your own risk.

