import requests, json
import pandas as pd
import datetime as dt

access_token = "eyJlbmMiOiJBMTI4Q0JDLUhTMjU2IiwiYWxnIjoiZGlyIn0..0ylXnfaMXPL4WaltVs05MA.mcWwUipn8peZipiPh5RVW1h8KSq3VOFuVVQA3FbRgzCah_PE394-bUXKnIwp0LXz0-Fip2uztfnGtBVxEqF-ZsrIlddArhilsNySYkEdR_2NfGA_SHITeZMbQ4mysmaudc5hJ7eiHF-mXGgRlrJL4tUsK3PQPOrB3vVVVSL-VrFw6raevL7-0VFsmG8AIGo5vOfPnEat3ogRQLcOeRuluN6fPV1yQHgbx42LGie_Q4g3Es3MdeIfYXavSHngyzW75lfORH2rhW41XDNNDinQNj5IJ038EPy9i7po5a4m9Ll_hnVU9IRSt-zrX8HOgPvKgRvhsalxSGMQ5f3eus4lLqjnaYWhvn-l9eebiP7LJcWnhVT2vQqnRrw6AVEI6PSdqLADiYlfxZcrfC_RrCLNNai4yC8QGMw5n8HHthRVO6FQklAUEt2oJyFKjwR9CA25L15WVtj9eXPw1ApbLWvxCvYjajuuaUssqOpYbbQ3MnOJ9Vq-aBX2wlZas_kZETFGie9mrsQ6Tb-uuXUgqT_s-PqtNqJtzlabNA7Q69RVuIAC0bN9Gsj5Oqd9ef_dmu9dgoW_bsXPQQQRXqE81RZjitafQBidma-mYbHpWur3FxsDShgRIW74ybI_NDGCClzhyfwnoKJ4cXACt2u1Zb6G4y6qcamk_zjYBb2xm84TnRUDAef7jcpFxlmrfIH0rurIqD7qkg0jpaYKaIqmxRuNhncm-BKqKDIP1YDKQzOfaM1eImzJTm8D_ZhLxGwhMuBT.UABxUxBi5C7E0OoTpwFg_Q"
base_url = "https://quickbooks.api.intuit.com"
realm_id = "13633946242997194"
report_name = "ProfitAndLoss"

# url = "/v3/company/13633946242997194/reports/ProfitAndLoss?accounting_method=Accrual&start_date=2023-01-01&end_date=2023-08-08&adjusted_gain_loss=true"

url = f"{base_url}/v3/company/{realm_id}/reports/{report_name}"
url2 = f"{base_url}/v3/company/{realm_id}/companyinfo/{realm_id}"

payload = {
    "accounting_method": "Accrual",
    "start_date": dt.datetime(2023,1,1).strftime("%Y-%m-%d"),
    "end_date": dt.datetime(2023,8,8).strftime("%Y-%m-%d"),
}
headers = {
    "Accept": "application/json",
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

res = requests.get(url, headers=headers, params=payload)
# res = requests.get(url2, headers=headers)
resobj = json.loads(res.text)


# function to try to extract this report into pandas dataframe
def extract_rows(item):
    extracted_rows = []
    if 'ColData' in item:
        amount = item['ColData'][1].get('value')
        extracted_rows.append({
            "LineItem": item['ColData'][0].get('value'),
            "Amount": float(amount) if (amount is not None and amount != '') else 0
        })
    elif isinstance(item, dict):
        for _, subitem in item.items():
            if isinstance(subitem, dict) or isinstance(subitem, list):
                exrows = extract_rows(subitem)
                extracted_rows += exrows
    elif isinstance(item, list):
        for _, subitem in enumerate(item):
            if isinstance(subitem, dict) or isinstance(subitem, list):
                exrows = extract_rows(subitem)
                extracted_rows += exrows
    return extracted_rows


rows = extract_rows(resobj)
df = pd.DataFrame(rows)
print(df)
