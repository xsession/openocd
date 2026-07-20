import socket
import threading
import time

from mchp_renode_cosim.protocol import ActionType, ProtocolMessage
from mchp_renode_cosim.socket_agent import CoSimSocketAgent, FirmwareCPUState


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    buf = bytearray(size)
    view = memoryview(buf)
    read = 0
    while read < size:
        n = sock.recv_into(view[read:])
        if n == 0:
            raise ConnectionError("socket closed")
        read += n
    return bytes(buf)


def test_socket_agent_handshake_and_basic_flow() -> None:
    main_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    async_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    main_listener.bind(("127.0.0.1", 0))
    async_listener.bind(("127.0.0.1", 0))

    main_listener.listen(1)
    async_listener.listen(1)

    host = "127.0.0.1"
    main_port = main_listener.getsockname()[1]
    async_port = async_listener.getsockname()[1]

    state = FirmwareCPUState(pc_reg=0)
    agent = CoSimSocketAgent(host=host, main_port=main_port, async_port=async_port, state=state)

    t = threading.Thread(target=lambda: (agent.connect(), agent.serve_forever()), daemon=True)
    t.start()

    main_conn, _ = main_listener.accept()
    async_conn, _ = async_listener.accept()

    main_conn.settimeout(1.0)
    async_conn.settimeout(1.0)

    # Renode sends handshake on main; agent responds on main.
    main_conn.sendall(ProtocolMessage(ActionType.Handshake, 0, 0, ProtocolMessage.NoPeripheralIndex).to_bytes())
    raw = _recv_exact(main_conn, 24)
    resp = ProtocolMessage.from_bytes(raw)
    assert resp.action == ActionType.Handshake

    # Set PC=10
    main_conn.sendall(ProtocolMessage(ActionType.RegisterSet, 0, 10, ProtocolMessage.NoPeripheralIndex).to_bytes())
    raw = _recv_exact(async_conn, 24)
    resp = ProtocolMessage.from_bytes(raw)
    assert resp.action == ActionType.RegisterSet

    # Step once -> PC increments.
    main_conn.sendall(ProtocolMessage(ActionType.Step, 0, 0, ProtocolMessage.NoPeripheralIndex).to_bytes())
    raw = _recv_exact(async_conn, 24)
    resp = ProtocolMessage.from_bytes(raw)
    assert resp.action == ActionType.Step

    main_conn.sendall(ProtocolMessage(ActionType.RegisterGet, 0, 0, ProtocolMessage.NoPeripheralIndex).to_bytes())
    raw = _recv_exact(async_conn, 24)
    resp = ProtocolMessage.from_bytes(raw)
    assert resp.action == ActionType.RegisterGet
    assert resp.data == 11

    # TickClock should execute some instructions when not halted/single-step.
    state.halted = False
    main_conn.sendall(ProtocolMessage(ActionType.TickClock, 0, 5, ProtocolMessage.NoPeripheralIndex).to_bytes())
    raw = _recv_exact(async_conn, 24)
    resp = ProtocolMessage.from_bytes(raw)
    assert resp.action == ActionType.TickClock
    assert resp.data == 5

    # Clean disconnect.
    main_conn.sendall(ProtocolMessage(ActionType.Disconnect, 0, 0, ProtocolMessage.NoPeripheralIndex).to_bytes())

    # Give the agent thread a moment to exit.
    t.join(timeout=1.0)
    assert not t.is_alive()

    main_conn.close()
    async_conn.close()
    main_listener.close()
    async_listener.close()
