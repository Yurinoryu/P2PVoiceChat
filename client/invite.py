import base64

def create_invite(ip):
    return base64.urlsafe_b64encode(ip.encode()).decode()

def parse_invite(code):
    return base64.urlsafe_b64decode(code.encode()).decode()
