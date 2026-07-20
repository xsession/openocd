from mchp_renode_cosim.protocol import ActionType, ProtocolMessage


def test_protocol_message_roundtrip() -> None:
    msg = ProtocolMessage(ActionType.RegisterSet, address=123, data=0x1122334455667788, peripheral_index=-1)
    raw = msg.to_bytes()
    assert len(raw) == 24

    decoded = ProtocolMessage.from_bytes(raw)
    assert decoded.action == ActionType.RegisterSet
    assert decoded.address == 123
    assert decoded.data == 0x1122334455667788
    assert decoded.peripheral_index == -1
