# Shioaji touch order extension


[![codecov](https://codecov.io/gh/SsallyLin/touchprice/branch/master/graph/badge.svg)](https://codecov.io/gh/SsallyLin/touchprice)



Touchprice is an extension feature of Shioaji. Using the conditions to trigger placing order.

## Installation

    pip install touchprice

## Quickstarts
Just import our API library like other popular python library and adding Shioaji to start using the feature of touchprice.

    import touchprice as tp
    import shioaji as sj

    api = sj.Shioaji()
    touch = tp.TouchOrder(api)
    
## Condition
TouchOrderCond contains touch condition and order condition. 

### Touch condition
    code="TXFC0",
    touch_price = 9985.0
    touch_cond=TouchCmd(code=code, price=touch_price)

### Order condition
    code="TXFD0",
    order = Order(
        action="Buy",
        price=-1,
        quantity=1,
        order_type="ROD",
        price_type="MKT",
        octype="Auto",
        )
    order_cond = OrderCmd(code=code, order=order)

### 
    condition = TouchOrderCond(
        touch_cmd = touch_cond, order_cmd = order_cond
        )

## Set condition to order     
    touch.set_condition(condition)

## Delete condition
    touch.delete_condition(condition)


