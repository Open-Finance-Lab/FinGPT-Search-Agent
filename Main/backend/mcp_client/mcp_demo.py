import json
import subprocess
import threading
import time

responses = {}
server_ready = threading.Event()
initialized_event = threading.Event()

def send_request(proc, method: str, params: dict, req_id: int):
    msg = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
        "params": params
    }
    s = json.dumps(msg) + "\n"
    proc.stdin.write(s.encode())
    proc.stdin.flush()

def read_responses(proc):
    for line in proc.stdout:
        line = line.decode().strip()
        if not line:
            continue
        # Checking for the server startup message
        if "Starting Yahoo Finance MCP server..." in line:
            server_ready.set()
        try:
            obj = json.loads(line)
            print("Response:", obj)
            if 'id' in obj:
                responses[obj['id']] = obj
            #trying to Detect 'initialized' notification (no id, method='initialized')
            elif 'method' in obj and obj['method'] == 'initialized':
                print("✅ Server sent initialized notification")
                initialized_event.set()
        except json.JSONDecodeError:
            # something wrong with the json getting back
            print("Malformed:", line)

# trying to wait for a specific response
def wait_for_response(req_id, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        if req_id in responses:
            return responses[req_id]
        time.sleep(0.1)
    raise TimeoutError(f"No response received for request ID {req_id}")

def main():
    # launches the mcp server
    proc = subprocess.Popen(
        ["uv", "run", "server.py"],
        cwd=r"C:\Users\andyy\OneDrive\Documents\GitHub\yahoo-finance-mcp",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    # Start reading stdout from the server
    t = threading.Thread(target=read_responses, args=(proc,), daemon=True)
    t.start()

    # waiting for the mcp server to be ready
    print("Waiting for MCP server to be ready...")
    server_ready.wait(timeout=10)
    # when the mcp server is started up and ready we send the initialize request
    print("MCP server is ready. Sending initialize...")

    # sending the initialize request
    send_request(proc, "initialize", {
        "protocolVersion": "1.0",
        "capabilities": {},
        "clientInfo": {
            "name": "mcp-demo",
            "version": "0.1"
        }
    }, req_id=0)

    # trying to wait for an initialize response
    try:
        init_response = wait_for_response(0)
        print("Initialized successfully")

        # setting a time limit for waiting for the initialized notification
        if initialized_event.wait(timeout=15):
            print("Server fully initialized (received 'initialized' notification), sending tool calls...")
        else:
            # the program will just continue to run if we dont get a notification
            print("Warning: Did not receive 'initialized' notification; proceeding anyway.")

    except TimeoutError as e:
        print("Initialization failed:", e)
        return

    # Trying to send tool calls, this is where theres errors

    #stock info call
    send_request(proc, "tools/call", {
        "name": "get_stock_info",
        "arguments": {
            "ticker": "AAPL"
        }
    }, req_id=1)

    #historical stock prices call
    send_request(proc, "tools/call", {
        "name": "get_historical_stock_prices",
        "arguments": {
            "ticker": "AAPL",
            "period": "1mo",
            "interval": "1d"
        }
    }, req_id=2)

    # giving some time to process the requests
    time.sleep(5)

if __name__ == "__main__":
    main()
