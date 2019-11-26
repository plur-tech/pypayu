import pytest
import requests
from pypayu import PayUApi, PayUError

@pytest.fixture()
def payu_api(requests_mock):
    requests_mock.post('https://secure.snd.payu.com/pl/standard/user/oauth/authorize', json={'access_token': 'token'})
    api = PayUApi('secret-login', 'wrong-password', sandbox=True)
    return api


def test_authentication(requests_mock):
    access_token = 'secret-access-token'
    requests_mock.post('https://secure.snd.payu.com/pl/standard/user/oauth/authorize', json={'access_token': access_token})
    api = PayUApi('secret-login', 'secret-password')
    # Check if request contains proper Authorization header
    requests_mock.get('https://secure.snd.payu.com/api/v2_1/paymethods', request_headers={'Authorization': f'Bearer {access_token}'}, json={})
    api.pay_methods()

def test_authentication_wrong_credentials(requests_mock):
    requests_mock.post('https://secure.snd.payu.com/pl/standard/user/oauth/authorize', status_code=401, json={'error': 'invalid_client', 'error_description': 'Bad client credentials'})
    with pytest.raises(PayUError) as payu_error:
        api = PayUApi('wrong', 'wrong')
    assert "Bad client credentials" in str(payu_error.value)

def test_sandbox_on_off(requests_mock):
    sandbox_token = 'sandbox_token'
    requests_mock.post('https://secure.snd.payu.com/pl/standard/user/oauth/authorize', json={'access_token': sandbox_token})
    api = PayUApi('secret-login', 'secret-password', sandbox=True)
    requests_mock.get('https://secure.snd.payu.com/api/v2_1/paymethods', request_headers={'Authorization': f'Bearer {sandbox_token}'}, json={})
    api.pay_methods()

    production_token = 'production_token'
    requests_mock.post('https://secure.payu.com/pl/standard/user/oauth/authorize', json={'access_token': production_token})
    api = PayUApi('secret-login', 'secret-password', sandbox=False)
    requests_mock.get('https://secure.payu.com/api/v2_1/paymethods', request_headers={'Authorization': f'Bearer {production_token}'}, json={})
    api.pay_methods()

def test_raise_for_status(requests_mock, payu_api):
    order_id='123456'
    error_resp = {'status': {'statusCode': "ERROR_ORDER_NOT_UNIQUE", 'statusDesc': "desc"}}
    requests_mock.get(f'/api/v2_1/orders/{order_id}', status_code=400, json=error_resp)
    with pytest.raises(PayUError) as payu_error:
        payu_api.order_status(order_id=order_id)
    assert payu_error.value.raw_error == error_resp
    assert "ERROR_ORDER_NOT_UNIQUE" in str(payu_error.value)

    requests_mock.get(f'/api/v2_1/orders/{order_id}', status_code=500)
    with pytest.raises(PayUError) as payu_error:
        payu_api.order_status(order_id=order_id)
    assert "RESPONSE FORMAT" in str(payu_error.value)

def test_params_send_with_request(requests_mock, payu_api):
    order_id='123456'
    def match_request_order_confirm_params(request):
        return request.json() == {"orderStatus": "COMPLETED"}
    requests_mock.put(f"/api/v2_1/orders/{order_id}/status", additional_matcher=match_request_order_confirm_params, json={'status': {'statusCode': "SUCCESS", 'statusDesc': "Status was updated"}})
    payu_api.order_confirm(order_id=order_id)

    def match_request_order_refund_params(request):
        return request.json() ==  {"refund": {"description": "Refund"}}
    requests_mock.post(f"/api/v2_1/orders/{order_id}/refunds", additional_matcher=match_request_order_refund_params, json={'status': {'statusCode': "SUCCESS", 'statusDesc': "Status was updated"}})
    payu_api.order_full_refund(order_id=order_id)

def test_partial_refound(requests_mock, payu_api):
    order_id='123456'
    def match_request_order_refund_params(request):
        return request.json() ==  {"refund": {"description": "Refund", "amount": 900}}
    requests_mock.post(f"/api/v2_1/orders/{order_id}/refunds", additional_matcher=match_request_order_refund_params, json={'status': {'statusCode': "SUCCESS", 'statusDesc': "Status was updated"}})
    payu_api.order_refund(order_id=order_id, data={"refund": {"description": "Refund", "amount": 900}})

def test_timeout_and_retries(requests_mock, payu_api):
    requests_mock.get('/api/v2_1/paymethods', exc=requests.exceptions.ConnectTimeout)
    with pytest.raises(requests.exceptions.ConnectTimeout):
        payu_api.pay_methods()
    assert requests_mock.call_count == 3

    requests_mock.get('/api/v2_1/paymethods', [
        {'exc':requests.exceptions.ConnectTimeout},
        {'json':
            { 
                "payByLinks":[ 
                { 
                    "value":"c",
                    "name":"Płatność online kartą płatniczą",
                    "brandImageUrl":"http://static.payu.com/images/mobile/logos/pbl_c.png",
                    "status":"ENABLED",
                    "minAmount": 50,
                    "maxAmount": 100000
                }
            ]
            }         
        },
    ])
    res = payu_api.pay_methods()
    assert res['payByLinks'][0]['name'] == "Płatność online kartą płatniczą"
    assert requests_mock.call_count == 5



