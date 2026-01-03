
import requests
import ipaddress



class IdentifiersObject(object):
    def __init__(self, identifiers: dict):
        self.identifiers = identifiers

    def get(self, key: str):
        return self.identifiers.get(key)
    



# ------------------------------------------------------

def infer_ip(ip: str):
    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError:
        return 'invalid'
    
    url = f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,district,zip,lat,lon,timezone,isp,org,as,asname,reverse,mobile,proxy,hosting,query"
    
    resp = requests.get(url, timeout=5)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") == "success":
        data['ip_version'] = 'ipv4' if ip_obj.version == 4 else ('ipv6' if ip_obj.version == 6 else '')
        return data
    else:
        return {"error": data.get("message", "")}
            
    


    





