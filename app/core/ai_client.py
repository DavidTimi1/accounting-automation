import requests
import json
import os
import time


def ask_ai(messages):
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    AI_MODEL = os.getenv("AI_MODEL")
    
    if not OPENROUTER_API_KEY:
        print("❌ OPENROUTER_API_KEY not found")
        return None
    
    if not AI_MODEL:
        print("❌ AI_MODEL not found")
        return None

    retry_count = 0
    max_retries = 3

    while retry_count < max_retries:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://davidtimi.tech",
                "X-OpenRouter-Title": "Account Logging App",
            },
            data=json.dumps({
                "model": AI_MODEL,
                "messages": messages,
                "max_tokens": 16_000
            }),
            timeout= 60 # 60 seconds
        )

        if response.status_code == 200:
            return response.json()
        else:
            retry_count += 1
            print(f"❌ AI Error: {response.status_code} - {response.text}")
            print(f"❌ Retrying... ({retry_count}/{max_retries})")
            time.sleep(1)

    raise Exception(f"❌ AI Error: {response.status_code} - {response.text}")


def ai_extract_invoice_data(full_invoices_text):
    system_prompt = """
    You are a precise data extraction engine. 
    Your ONLY job is to extract financial data from raw invoice text and return it as a JSON object.
    Do NOT include any conversational filler, greetings, or explanations.

    JSON STRUCTURE FOR EACH INVOICE:
    {
        "batch": "month batch for the invoice e.g: Apr 26, May 25, etc. just that exact format, abbr month, no day!"
        "date": "Ddd-Mmm no year needed e.g 4th Aug, or 4th-8th Aug or 4th-5th NOTE THAT THE MONTH IS NOT IN FULL HERE TOO",
        "venue": "Name of the location/restaurant (e.g. Eko Hotels)",
            hint: wrtten after VENUE: until the line ends or another section starts.
        "client_name": "Name of the client/company 
            hint: Find the text after the ATT section and grab the client name that appears just before the Date column. else it appears after ATT before the colun separator”",
        "event": "Name of the event",
        "amount_payable": "the final amount to be paid, whether it says'AMOUNT' or 'AMOUNT PAYABLE', and extract the number.",
        "discount": "Total discount (float)",
        "total_cost": in a situation where the invoice has discont, the total cost will be provided",
        "vat": "Total VAT charged (float)",
        "logistics": "Total logistic/service charge (float)",
        "rep": "3 letters name code of the referrer, usually in the filename (not the client) e.g JUL",
        "referrer": "same as rep",
        "remark": "a really brief of additional notes or descriptions. when there is a discount it should be: discount given/TODO"
        "extra": "if there is a discount, it will be in thsi format:- 10000.0 Discount, TOTAL: 10000.0, "
    }
    Response should be as a list of invoice_json objects: 
    [
        {...},
        {...},
        {...}
    ]

    RULES:
    1. If a field is missing, return null for that field.
    2. service charge is also called logistic charge or logistics charge.
    3. 'amount_payable', 'discount', 'total_cost', 'vat', 'service_charge' are numeric and should be gotten directly from the invoice text, do not calculate them.
    4. Do not hallucinate or try to fix any name, client names are actually companies sometimes.
    5. Dont use null for any field, use an empty string ""
    6. preserve the order of invoices
    7. MAKE NO MISTAKES!!
    """

    try:
        user_prompt = f"""
        Extract the data from this invoice text:

        {full_invoices_text}

        Return ONLY the JSON object.
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = ask_ai(messages)
        
        # Navigate the response structure
        if isinstance(response, dict):
            # Handle OpenAI standard response
            if "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0].get("message", {}).get("content", "{}")
            # Handle raw response if it's already the content
            else:
                content = response
        else:
            content = "[]"
            
        # Clean up and parse JSON
        # Remove markdown code blocks if AI wraps them (e.g., ```json ... ```)
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        data = json.loads(content)
        return data

    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        print(f"Raw Content: {content}")
        return None
    except Exception as e:
        return None
