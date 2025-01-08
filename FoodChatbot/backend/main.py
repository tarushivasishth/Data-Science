from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
import uvicorn
import db_helper
import generic_helper

app = FastAPI()

@app.post("/")
async def handle_request(request: Request):
    # Retrieve JSON data from the request
    payload = await request.json()

    # extract the necessary information from the payload
    # based on the structure of the Webhookequest from Dialogflow
    intent = payload['queryResult']['intent']['displayName']
    parameters = payload['queryResult']['parameters']
    output_contexts = payload['queryResult']['outputContexts']
    session_id = generic_helper.extract_session_id(output_contexts[0]["name"])

    if intent == "track.order-context:ongoing-tracking":
        return track_order(parameters)
    elif intent == "order.add":
        return add_orders(parameters,session_id)
    elif intent == "order.complete-context:ongoing-order":
        return complete_orders(parameters,session_id)
    elif intent == "order.remove":
        return remove_orders(parameters,session_id)

inprocess_orders = {}
# format of inprocess_orders = {
#       "session_id_1": {"pizza": 1, "samosa": 2},
#       "session_id_2": {"chhole bhature": 1, "mango lassi": 2}}

def save_to_db(order: dict):
    next_order_id = db_helper.get_next_order_id()

    for food_item, quantity in order.items():
        rcode = db_helper.insert_order_item(
            food_item,
            quantity,
            next_order_id
        )

        if rcode == -1:
            return -1
        
    db_helper.insert_order_tracking(next_order_id,"in progress")

    return next_order_id

# step1: locate the session id record: "session_id_1": {"pizza": 1, "samosa": 2}
# step2: get the value from dict: {"pizza": 1, "samosa": 2}
# step3: remove the food_items: request: ["samosa"]

def remove_orders(parameters,session_id):
    if session_id not in inprocess_orders:
        fulfillment_text = "I'm having a trouble finding your order. Sorry! Can you place a new order please?"
    else:
        current_order = inprocess_orders[session_id]
        food_items = parameters["food-item"]

        removed_items = []
        no_such_items = []
        for item in food_items:
            if item not in current_order:
                no_such_items.append(item)
            else:
                removed_items.append(item)
                del current_order[item]
        
        if len(removed_items) > 0:
            fulfillment_text = f'Removed {", ".join(removed_items)} from your order!'
        if len(no_such_items) > 0:
            fulfillment_text = f' Your current order does not have {', '.join(no_such_items)}.'
        if len(current_order.keys()) == 0:
            fulfillment_text += " Your order is empty!"
        else:
            order_str = generic_helper.get_str_from_food_dict(current_order)
            fulfillment_text += f" Now, your current order is: {order_str}"

    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })
            
# step1: get order id
# step2: add items to the db calling insert_order_item()
# step3: get the total order price from food_items table using get_total_order_price() user defined function
# step4: add the order status to order tracking table
# step5: then delete inprocess_orders[session_id]

def complete_orders(parameters,session_id):
    if session_id not in inprocess_orders:
        fulfillment_text = "I'm having a trouble finding your order. Sorry! Can you place a new order please?"
    else:
        order = inprocess_orders[session_id]
        order_id = save_to_db(order)
        if order_id == -1:
            fulfillment_text = "Sorry, I couldn't process your order due to a backend error. " \
                               "Please place a new order again"
        else:
            order_total = db_helper.get_total_order_price(order_id)
            order_str = generic_helper.get_str_from_food_dict(inprocess_orders[session_id])

            fulfillment_text = f"Awesome. We have placed your order. " \
                           f"Your order is: {order_str}. " \
                           f"Here is your order id {order_id}. " \
                           f"Your order total is ${order_total} which you can pay at the time of delivery!"
        del inprocess_orders[session_id]
    
    return JSONResponse(content= {
        "fulfillmentText": fulfillment_text
    })

def add_orders(parameters,session_id):
    food_items = parameters["food-item"]
    quantity = parameters["number"]

    if len(food_items) != len(quantity):
        fulfillment_text = "Sorry I didn't understand. Can you please specify food items and quantities clearly?"
    else:
        new_order_dict = dict(zip(food_items,quantity))

        if session_id in inprocess_orders:
            current_order_dict = inprocess_orders[session_id]
            current_order_dict.update(new_order_dict)
        else:
            inprocess_orders[session_id] = new_order_dict
        print(inprocess_orders)
        order_str = generic_helper.get_str_from_food_dict(inprocess_orders[session_id])
        fulfillment_text = f"So far you have: {order_str}. Do you need anything else?"
     
    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })


def track_order(parameters):
    order_id = parameters['order_id']
    order_status = db_helper.get_order_status(order_id)

    if order_status:
        fulfillment_text = f"The order status for order id {order_id} is : {order_status}"
    else:
        fulfillment_text = f"No order found with order id: {order_id}"

    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })

# 1) We can create another intent for cancelling the orders using order id by creating 2 intents that will have a different context like ongoing-cancellation:
# one intent will ask for order id and the other intent will take order id as input, deletes the row with that id in the backend(db) and then prints some fulfillment text

# 2) Fix the issue with incomplete order. Remove the previous added items in the inprocess_orders under same session_id if someone says new order.

# 3) Create a 3rd option in which the dialogflow displays the store hours as a fized response
