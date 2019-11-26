__version__ = '0.1.0'

import uplink

class PayUError(Exception):
    pass

def no_redirects(response):
    if response.history:
        return response.history[0]
    return response

def raise_for_status(response):
    if 200 <= response.status_code < 400:
        return response
    try:
        error_data = response.json()
    except:
        raise PayUError(f"{response.url} - RESPONSE FORMAT")
    if all(elem in error_data.keys() for elem in ('error', 'error_description')):
        raise PayUError(f"{response.url} - {error_data['error']}: {error_data['error_description']}")
    elif 'status' in error_data:
        raise PayUError(f"{response.url} - {error_data['status']['statusCode']}: {error_data['status']['statusDesc']}")
    raise PayUError(f"{response.url} - UNKNOWN ERROR")

@uplink.returns.json
@uplink.response_handler(raise_for_status)
@uplink.retry(on_exception=uplink.retry.CONNECTION_TIMEOUT, max_attempts=2)
@uplink.timeout(4)
class PayUApi(uplink.Consumer):
    
    @uplink.params({"grant_type": "client_credentials"})
    @uplink.post("/pl/standard/user/oauth/authorize")
    def authorize(self, client_id: uplink.Query("client_id"), client_secret: uplink.Query("client_secret")):
        pass
    
    @uplink.get("/api/v2_1/paymethods")
    def pay_methods(self):
        pass
    
    @uplink.get("/api/v2_1/orders/{order_id}")
    def order_status(self, order_id):
        pass
    
    @uplink.json
    @uplink.response_handler(no_redirects)
    @uplink.post("/api/v2_1/orders")
    def create_order(self, order_info: uplink.Body):
        pass

    @uplink.delete("/api/v2_1/orders/{order_id}")
    def order_cancel(self, order_id):
        pass

    @uplink.json
    @uplink.post("/api/v2_1/orders/{order_id}/refunds")
    def order_full_refund(self, order_id, data: uplink.Body = {"refund": {"description": "Refund"}}):
        pass

    @uplink.json
    @uplink.post("/api/v2_1/orders/{order_id}/refunds")
    def order_refund(self, order_id, data: uplink.Body):
        pass

    @uplink.get("/api/v2_1/orders/{order_id}/transactions")
    def get_transactions(self, order_id):
        pass

    @uplink.json
    @uplink.put("/api/v2_1/orders/{order_id}/status")
    def order_confirm(self, order_id, data: uplink.Body = {"orderStatus": "COMPLETED"}):
        pass
    
    def __init__(self, client_id, client_secret, sandbox=True, **kwargs):
        if sandbox:
            kwargs['base_url'] = 'https://secure.snd.payu.com'
        else:
            kwargs['base_url'] = 'https://secure.payu.com'
        super().__init__(**kwargs)
        response = self.authorize(client_id, client_secret)
        access_token = response['access_token']
        self.session.headers["Authorization"] = f'Bearer {access_token}'