# Author: Dhaval Patel. Codebasics YouTube Channel

import re

def get_str_from_food_dict(food_dict: dict):
    result = ", ".join([f"{int(value)} {key}" for key,value in food_dict.items()])
    return result


def extract_session_id(session_str: str):
    match = re.search(r"/sessions/(.*?)/contexts/", session_str)
    if match:
        extracted_string = match.group(1)
        return extracted_string

    return ""

# if __name__ == '__main__':
# print(get_str_from_food_dict({"samosa":1,"chhole bhature": 3}))
    # print(extract_session_id("projects/meera-chatbot-food-delive-lhon/agent/sessions/2cf03e8b-8a11-8c41-06e7-7863e243604f/contexts/ongoing-order"))
