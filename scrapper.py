# in progress

import requests
url ="https://www.businessinsider.com/chinese-construction-risks-turning-the-yellow-sea-into-flashpoint-2025-2"
resp = requests.get(url)
print(resp.text)
file = open("news.html", "w")
file.write(resp.text)
file.close()

    