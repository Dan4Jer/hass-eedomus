import requests
url="http://192.168.1.2/api/get?action=auth.test&api_user=4pYrgk&api_secret=ChJKkudDrYhoh2NR"
r=requests.get(url,timeout=4)
print(r.status_code, r.text)
