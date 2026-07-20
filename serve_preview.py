import functools, http.server, os

PORT = int(os.environ.get("PORT", "8000"))
DIR = os.environ.get("PREVIEW_DIR", r"C:\Projects\foundry\output\sites\mindsgate-redesign")
Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=DIR)

# ThreadingHTTPServer: one slow/stuck client (browser preconnect, hung fetch)
# no longer blocks accept() — the single-threaded TCPServer version froze with
# "connection refused" while still holding the port.
with http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler) as httpd:
    print(f"serving {DIR} on {PORT}")
    httpd.serve_forever()
