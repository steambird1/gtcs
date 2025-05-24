from urllib import request, parse
import traceback

url = 'http://localhost:6160/'
cur = ""
while True:
    try:
        data = input(">>> ")
        if data == "":
            cur += "####"
            cd = cur.encode()
            req = request.Request(url, cd)
            resp = request.urlopen(req)
            rs = resp.read()
            cur = ""
            print(rs.decode('utf-8'))
        else:
            cur += data + "\n"
    except Exception as e:
        print("<ERROR>",str(e))
        traceback.print_exc()