# Shioaji touch order extension

[![PyPI - Status](https://img.shields.io/pypi/v/touchprice.svg?)](https://pypi.org/project/touchprice)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/touchprice.svg)]()
[![PyPI - Downloads](https://img.shields.io/pypi/dm/touchprice.svg?)](https://pypi.org/project/touchprice)
[![codecov](https://codecov.io/gh/SsallyLin/touchprice/branch/master/graph/badge.svg)](https://codecov.io/gh/SsallyLin/touchprice)



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
touch = tp.TouchOrder(api)
```   
## Condition
TouchOrderCond contains touch condition and order condition. 

### Touch condition
#### TouchCmd arg:
* code: str,

* close: touchprice.touch_price.Price = None,
* buy_price: touchprice.touch_price.Price = None,
* sell_price: touchprice.touch_price.Price = None,
* high: touchprice.touch_price.Price = None,
* low: touchprice.touch_price.Price = None,
* volume: touchprice.touch_price.Qty = None,
* total_volume: touchprice.touch_price.Qty = None,

```
touch_cmd = 
    touchprice.TouchCmd(
        code="2890", 
        close = touchprice.Price(price=11.0, trend="Up")
    )
```

#### Price arg
* price: float = 0.0,
* trend: touchprice.touch_price.Trend = 'Equal' ('Up', 'Down', 'Equal')
* price_type: touchprice.touch_price.PriceType = 'LimitPrice' ('LimitPrice', 'LimitUp', 'Unchanged ', 'LimitDown ')

#### Qty arg
* qty: int,
* trend: touchprice.touch_price.Trend = 'Equal'('Up', 'Down', 'Equal')




### Order condition
### OrderCmd arg
* code: str
* order: shioaji.Order
```
order_cmd = touchprice.OrderCmd(
    code="2890",
    order = Order(
        action="Buy",
        price=10,
        quantity=1,
        order_type="ROD",
        price_type="LMT",
    )

```



## Set condition to order    
```
condition = touchprice.TouchOrderCond(
                touch_cmd = touch_cond, 
                order_cmd = order_cond
            )
touch.set_condition(condition)
``` 
    

## Delete condition
    touchprice.delete_condition(condition)

## Show condition
If not set code can show all conditions, else just show coditions of code. 
``` 
touchprice.show_condition(code)
``` 
