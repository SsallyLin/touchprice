# Shioaji touch order extension

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
    touch_contract = Future(
        code="TXFC0",
        symbol="TXF202003",
        name="臺股期貨",
        category="TXF",
        delivery_month="202003",
        underlying_k
        ind="I",
        )

    touch_price = 9985.0
    touch_cond=TouchCmd(contract=touch_contract, price=touch_price)

### Order condition
    order_contract = Future(
        code="TXFD0",
        symbol="TXF202004",
        name="臺股期貨",
        category="TXF",
        delivery_month="202004",
        underlying_k
        ind="I",
        )
    order = Order(
        action="Buy",
        price=-1,
        quantity=1,
        order_type="ROD",
        price_type="MKT",
        octype="Auto",
        )
    order_cond = OrderCmd(contract=order_contract, order=order)

### 
    condition = TouchOrderCond(
        touch_cmd = touch_cond, order_cmd = order_cond
        )

## Set condition to order     
    touch.set_condition(condition)

## Delete condition
    touch.delete_condition(condition)

## Show condition
    touch.show_conditions()

