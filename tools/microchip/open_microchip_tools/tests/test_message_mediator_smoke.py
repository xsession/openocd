import os
import tempfile
import unittest

from mchp_mdbcore import (
    ActionList,
    Message,
    MessageMediator,
    PropertiesFileImpl,
    clear_default_listeners,
    register_default_listener,
)


class _ListenerA:
    def __init__(self):
        self.calls = []

    def handleMessage(self, paramMessage, paramInt):
        self.calls.append((paramMessage.getMessageString(), paramInt))
        return -1


class _ListenerB:
    def __init__(self, ret=123):
        self.calls = []
        self.ret = ret

    def handleMessage(self, paramMessage, paramInt):
        self.calls.append((paramMessage.getMessageString(), paramInt))
        return self.ret


class _SettingsListener:
    def __init__(self):
        self.clear_titles = []
        self.remove_titles = []

    def handleMessage(self, paramMessage, paramInt):
        return -1

    def SetClearOutputWindowOnNewSession(self, paramString):
        self.clear_titles.append(paramString)

    def RemoveClearOutputWindowOnNewSession(self, paramString):
        self.remove_titles.append(paramString)


class TestMessageMediatorSmoke(unittest.TestCase):
    def setUp(self):
        clear_default_listeners()

    def tearDown(self):
        clear_default_listeners()

    def test_first_non_minus_one_wins(self):
        a = _ListenerA()
        b = _ListenerB(ret=77)
        register_default_listener(a)
        register_default_listener(b)

        mm = MessageMediator()
        msg = Message("hello")
        ret = mm.handleMessage(msg, ActionList.DefaultActionID)

        self.assertEqual(ret, 77)
        self.assertEqual(len(a.calls), 1)
        self.assertEqual(len(b.calls), 1)

    def test_suppressed_short_circuits_to_zero(self):
        with tempfile.TemporaryDirectory() as td:
            memo_path = os.path.join(td, "suppressed.properties")
            memo = PropertiesFileImpl(memo_path)

            a = _ListenerA()
            register_default_listener(a)

            msg = Message("will not be delivered")
            msg.makeSuppressible(memo, "prov", "key")
            msg.setSuppressed()

            mm = MessageMediator(memo=memo)
            ret = mm.handleMessage(msg, ActionList.DefaultActionID)

            self.assertEqual(ret, 0)
            self.assertEqual(a.calls, [])

    def test_settings_are_forwarded(self):
        s = _SettingsListener()
        register_default_listener(s)

        mm = MessageMediator()
        mm.SetClearOutputWindowOnNewSession("Output")
        mm.RemoveClearOutputWindowOnNewSession("Output")

        self.assertEqual(s.clear_titles, ["Output"])
        self.assertEqual(s.remove_titles, ["Output"])

    def test_legacy_import_path(self):
        from com.microchip.mplab.mdbcore.MessageMediator import MessageMediator as LegacyMM

        mm = LegacyMM()
        self.assertTrue(hasattr(mm, "handleMessage"))


if __name__ == "__main__":
    unittest.main()
