import requests

API_URL = "http://127.0.0.1:8000"
USERNAME = "admin123"
PASSWORD = "kiko123321"

# 1. Вземи токен
auth_response = requests.post(
    f"{API_URL}/auth/token",
    data={"username": USERNAME, "password": PASSWORD},
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)

token = auth_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Данни за ваксини
vaccines = [
    {"name": "6-валентна (1)", "is_mandatory": True, "recommended_month": 2},
    {"name": "6-валентна (2)", "is_mandatory": True, "recommended_month": 3},
    {"name": "6-валентна (3)", "is_mandatory": True, "recommended_month": 4},
    {"name": "Пневмококова (1)", "is_mandatory": True, "recommended_month": 2},
    {"name": "Пневмококова (2)", "is_mandatory": True, "recommended_month": 4},
    {"name": "Пневмококова (реимунизация)", "is_mandatory": True, "recommended_month": 18},
    {"name": "Ротавирус (1)", "is_mandatory": False, "recommended_month": 2},
    {"name": "Ротавирус (2)", "is_mandatory": False, "recommended_month": 3},
    {"name": "МПР", "is_mandatory": True, "recommended_month": 13},
    {"name": "5-валентна (реимунизация)", "is_mandatory": True, "recommended_month": 18}
]

# 3. Изпращане към API-то
for v in vaccines:
    r = requests.post(f"{API_URL}/vaccines/", json=v, headers=headers)
    print(f"{v['name']}: {r.status_code} - {r.text}")



