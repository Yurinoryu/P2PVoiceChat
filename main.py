import sys

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print(" python main.py host")
        print(" python main.py client")

    mode = sys.argv[1]

    if mode == "host":

        from host.host_server import start_server
        start_server()

    elif mode == "client":

        from client.client import start_client
        start_client()

    else:
        print("Unknown mode")

if __name__ == "__main__":
    main()
