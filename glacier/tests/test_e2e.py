"""End-to-end: fake OpenAI-compatible LLM -> brain compat engine -> real tools -> local API server."""
import json, os, sys, tempfile, threading, unittest, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

D = tempfile.mkdtemp()
os.environ.update(GLACIER_DATA_DIR=D, API_SERVER_ENABLED="true", API_SERVER_PORT="18765",
                  AUTO_DETECT_OLLAMA="false", GEMINI_API_KEY="")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakeLLM(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        last = body["messages"][-1]
        if last["role"] == "tool":
            msg = {"role": "assistant", "content": "Result: " + last["content"][:60]}
        else:
            msg = {"role": "assistant", "content": None, "tool_calls": [
                {"id": "c1", "type": "function", "function": {"name": "calculate", "arguments": json.dumps({"expression": "6*7"})}}]}
        out = json.dumps({"choices": [{"message": msg}]}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)


srv = HTTPServer(("127.0.0.1", 18999), FakeLLM)
threading.Thread(target=srv.serve_forever, daemon=True).start()
os.environ["OPENAI_COMPAT_BASE_URL"] = "http://127.0.0.1:18999/v1"

import brain, config
from channels import api_server


class E2E(unittest.TestCase):
    def test_brain_tool_loop(self):
        r = brain.ask_glacier("6 guna 7 kitna hota hai", session="e2e")
        self.assertIn("42", r)

    def test_api_server(self):
        self.assertTrue(api_server.start())
        tok = api_server.get_token()
        req = urllib.request.Request("http://127.0.0.1:18765/ask", data=json.dumps({"text": "6*7?"}).encode(),
                                     headers={"X-Glacier-Token": tok})
        self.assertIn("42", json.load(urllib.request.urlopen(req))["reply"])
        bad = urllib.request.Request("http://127.0.0.1:18765/ask", data=b"{}", headers={"X-Glacier-Token": "nope"})
        with self.assertRaises(urllib.error.HTTPError) as c:
            urllib.request.urlopen(bad)
        self.assertEqual(c.exception.code, 401)


if __name__ == "__main__":
    unittest.main()
