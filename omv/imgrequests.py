import usocket
import ubinascii
import ujson
from led import blue_led, red_led

class Response:
    def __init__(self, code, reason, headers=None, content=None):
        self.encoding = "utf-8"
        self._content = content
        self._headers = headers
        self.reason = reason
        self.status_code = code

    @property
    def headers(self):
        return str(self._headers, self.encoding)

    @property
    def content(self):
        return str(self._content, self.encoding)

    def json(self):
        return ujson.loads(self._content)


def readline(s):
    l = bytearray()
    while True:
        try:
            l += s.read(1)
            if l[-1] == b"\n":
                break
        except:
            break
    return l


def socket_readall(s):
    buf = b""
    while True:
        recv = b""
        try:
            recv = s.recv(1)
        except:
            pass
        if len(recv) == 0:
            break
        buf += recv
    return buf


def write_empty_body(s):
    s.write(b"\r\n")


def write_json_body(s, json):
    s.write(b"Content-Type: application/json\r\n")
    data = ujson.dumps(json)
    s.write(b"Content-Length: %d\r\n\r\n" % len(data))
    s.write(data)


def write_image_body(s, image_bytes):
    s.write(b"Content-Type: image/jpeg\r\n")
    s.write(b"Content-Length: %d\r\n\r\n" % len(image_bytes))
    s.write(image_bytes)


def request(method, url, json=None, image_bytes=None, headers={}, auth=None, stream=None):
    blue_led.on()

    try:
        proto, _, host, path = url.split("/", 3)
    except ValueError:
        proto, _, host = url.split("/", 2)
        path = ""
    if proto == "http:":
        port = 80
    elif proto == "https:":
        import ussl

        port = 443
    else:
        raise ValueError("Unsupported protocol: " + proto)

    if ":" in host:
        host, port = host.split(":", 1)
        port = int(port)

    if auth:
        headers["Authorization"] = b"Basic %s" % (
            ubinascii.b2a_base64("%s:%s" % (auth[0], auth[1]))[0:-1]
        )

    resp_code = 0
    resp_reason = None
    resp_headers = []

    ai = usocket.getaddrinfo(host, port)[0]
    s = usocket.socket(ai[0], ai[1], ai[2])
    try:
        s.connect(ai[-1])
        s.settimeout(5.0)
        if proto == "https:":
            s = ussl.wrap_socket(s, server_hostname=host)

        s.write(b"%s /%s HTTP/1.0\r\n" % (method, path))

        if "Host" not in headers:
            s.write(b"Host: %s\r\n" % host)

        # Iterate over keys to avoid tuple alloc
        for k in headers:
            s.write(k)
            s.write(b": ")
            s.write(headers[k])
            s.write(b"\r\n")

        if json is not None:
            write_json_body(s, json)
        elif image_bytes is not None:
            write_image_body(s, image_bytes)
        else:
            write_empty_body(s)

        response = socket_readall(s).split(b"\r\n")
        while response:
            l = response.pop(0).strip()
            if not l or l == b"\r\n":
                break
            if l.startswith(b"Transfer-Encoding:"):
                if b"chunked" in l:
                    raise ValueError("Unsupported " + l)
            elif l.startswith(b"Location:"):
                raise NotImplementedError("Redirects not yet supported")
            if "HTTPS" in l or "HTTP" in l:
                sline = l.split(None, 2)
                resp_code = int(sline[1])
                resp_reason = sline[2].decode().rstrip() if len(sline) > 2 else ""
                continue
            resp_headers.append(l)
        resp_headers = b"\r\n".join(resp_headers)
        content = b"\r\n".join(response)
    except OSError:
        s.close()
        red_led.on()
        raise
    
    blue_led.off()
    return Response(resp_code, resp_reason, resp_headers, content)
