from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Protocol, Tuple, runtime_checkable


@dataclass(frozen=True)
class Color:
    r: int
    g: int
    b: int


BLACK = Color(0, 0, 0)


class ActionList:
    DoNothing = 0
    DefaultActionID = 1
    OutputWindowOnly = 2
    OutputWindowOnlyDisplayMessage = 3
    OutputWindowOnlyDisplayError = 4
    OutputWindowOnlyDisplayColor = 5
    OutputWindowOnlyDisplayErrorLink = 6
    FocusOnViewOnly = 7
    FocusOnViewAndOutPutWindowMessage = 8
    FocusOnViewAndOutPutWindowError = 9
    FocusOnViewAndOutPutWindowColor = 10
    FocusOnViewAndOutPutWindowErrorLink = 11
    DialogPopupOnly = 12
    DialogPopupAndOutputWindowMessage = 13
    DialogPopupAndOutputWindowError = 14
    DialogPopupAndOutputWindowColor = 15
    DialogPopupAndOutputWindowErrorLink = 16
    FocusOnViewDialogPopupAndOutputWindowMessage = 17
    FocusOnViewDialogPopupAndOutputWindowError = 18
    FocusOnViewDialogPopupAndOutputWindowColor = 19
    FocusOnViewDialogPopupAndOutputWindowErrorLink = 20
    OutputWindowDisplayErrorLink_FocusOnViewOnClick = 21
    OutputWindowDisplayErrorLink_OpenSourceFileOnClick = 22
    OutputWindowDisplayErrorLink_InfoDialogPopupOnClick = 23


@runtime_checkable
class SuppressibleMessageMemo(Protocol):
    def isMessageSuppressed(self, providerKey: str, messageKey: str) -> bool:
        ...

    def setMessageSuppressed(self, providerKey: str, messageKey: str, isSuppressed: bool) -> None:
        ...

    def setMessageSuppressedWithoutSaving(
        self, providerKey: str, messageKey: str, isSuppressed: bool
    ) -> None:
        ...

    def save(self) -> None:
        ...


class NbPreferencesImpl(SuppressibleMessageMemo):
    _store: Dict[Tuple[str, str], str] = {}

    def isMessageSuppressed(self, providerKey: str, messageKey: str) -> bool:
        value = self._store.get((providerKey, messageKey))
        return value is not None and value == "true"

    def setMessageSuppressed(self, providerKey: str, messageKey: str, isSuppressed: bool) -> None:
        self._store[(providerKey, messageKey)] = "true" if isSuppressed else "false"

    def setMessageSuppressedWithoutSaving(
        self, providerKey: str, messageKey: str, isSuppressed: bool
    ) -> None:
        self.setMessageSuppressed(providerKey, messageKey, isSuppressed)

    def save(self) -> None:
        return


class PropertiesFileImpl(SuppressibleMessageMemo):
    def __init__(self, fileName: str):
        self.fileName = str(fileName)
        self._path = Path(self.fileName)
        self.props: Dict[str, str] = {}
        try:
            self._load()
        except OSError:
            pass

    def _load(self) -> None:
        if not self._path.exists():
            return
        text = self._path.read_text(encoding="utf-8", errors="replace")
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith("!"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
            elif ":" in line:
                key, value = line.split(":", 1)
            else:
                continue
            self.props[key.strip()] = value.strip()

    def isMessageSuppressed(self, providerKey: str, messageKey: str) -> bool:
        value = self.props.get(f"{providerKey}/{messageKey}")
        return value is not None and value == "true"

    def setMessageSuppressed(self, providerKey: str, messageKey: str, isSuppressed: bool) -> None:
        self.setMessageSuppressedWithoutSaving(providerKey, messageKey, isSuppressed)
        self.save()

    def setMessageSuppressedWithoutSaving(
        self, providerKey: str, messageKey: str, isSuppressed: bool
    ) -> None:
        self.props[f"{providerKey}/{messageKey}"] = "true" if isSuppressed else "false"

    def save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            lines = [f"{k}={v}" for k, v in sorted(self.props.items())]
            self._path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        except OSError:
            return


class Message:
    def __init__(
        self,
        MessageText: str = "",
        Title: str = "",
        colorOfText: Color = BLACK,
        clearOutputWindow: bool = False,
        closeIOStream: bool = False,
        forceSelectTab: bool = False,
        view: Optional[str] = None,
        propertyName: Optional[str] = None,
        typeOfDialog: int = 1,
    ):
        self.strMessage = MessageText
        self.strTitle = Title
        self.textColor = colorOfText
        self.viewToFocus = view
        self.strPropertyName = propertyName
        self.dialogBoxType = typeOfDialog
        self.blnClear = clearOutputWindow
        self.blnCloseIO = closeIOStream
        self.blnForceSelectTab = forceSelectTab

        self.memo: Optional[SuppressibleMessageMemo] = None
        self.providerKey: Optional[str] = None
        self.messageKey: Optional[str] = None

        self.associatedFile: Optional[str] = None
        self.associatedLine: int = 0

    def setMessageString(self, str: str) -> None:
        self.strMessage = str

    def setTextColorForOutputWindow(self, textColor: Color) -> None:
        self.textColor = textColor

    def setClearOutputWindow(self, clearOutputWindow: bool) -> None:
        self.blnClear = clearOutputWindow

    def setTitle(self, Title: str) -> None:
        self.strTitle = Title

    def setViewToFocus(self, view: Optional[str]) -> None:
        self.viewToFocus = view

    def setPropertyName(self, propertyName: Optional[str]) -> None:
        self.strPropertyName = propertyName

    def setDialogBoxType(self, typeOfDialogBox: int) -> None:
        self.dialogBoxType = typeOfDialogBox

    def setCloseIOStream(self, closeIOStream: bool) -> None:
        self.blnCloseIO = closeIOStream

    def setForceSelectTab(self, forceSelectTab: bool) -> None:
        self.blnForceSelectTab = forceSelectTab

    def getMessageString(self) -> str:
        return self.strMessage

    def getTextColorForOutputWindow(self) -> Color:
        return self.textColor

    def getTitle(self) -> str:
        return self.strTitle

    def getViewToFocus(self) -> Optional[str]:
        return self.viewToFocus

    def getPropertyName(self) -> Optional[str]:
        return self.strPropertyName

    def getDialogBoxType(self) -> int:
        return self.dialogBoxType

    def getClearOutputWindow(self) -> bool:
        return self.blnClear

    def getCloseIO(self) -> bool:
        return self.blnCloseIO

    def getForceSelectTab(self) -> bool:
        return self.blnForceSelectTab

    def makeSuppressible(self, memo: SuppressibleMessageMemo, providerKey: str, messageKey: str) -> None:
        self.memo = memo
        self.providerKey = providerKey
        self.messageKey = messageKey

    def isSuppressible(self) -> bool:
        return self.memo is not None

    def isSuppressed(self) -> bool:
        if self.memo is not None and self.providerKey is not None and self.messageKey is not None:
            return self.memo.isMessageSuppressed(self.providerKey, self.messageKey)
        return False

    def setSuppressed(self) -> None:
        if self.memo is not None and self.providerKey is not None and self.messageKey is not None:
            self.memo.setMessageSuppressed(self.providerKey, self.messageKey, True)

    def SetFileAndLine(self, f: str, l: int) -> None:
        self.associatedFile = f
        self.associatedLine = int(l)

    def GetAssociatedFile(self) -> Optional[str]:
        return self.associatedFile

    def GetAssociatedLine(self) -> int:
        return self.associatedLine


@runtime_checkable
class MessageMediatorListener(Protocol):
    def handleMessage(self, paramMessage: Message, paramInt: int) -> int:
        ...


@runtime_checkable
class MessageMediatorSettings(Protocol):
    def SetClearOutputWindowOnNewSession(self, paramString: str) -> None:
        ...

    def RemoveClearOutputWindowOnNewSession(self, paramString: str) -> None:
        ...


_DEFAULT_LISTENERS: List[MessageMediatorListener] = []


def register_default_listener(listener: MessageMediatorListener) -> None:
    if listener not in _DEFAULT_LISTENERS:
        _DEFAULT_LISTENERS.append(listener)


def unregister_default_listener(listener: MessageMediatorListener) -> None:
    try:
        _DEFAULT_LISTENERS.remove(listener)
    except ValueError:
        return


def clear_default_listeners() -> None:
    _DEFAULT_LISTENERS.clear()


class MessageMediator(MessageMediatorSettings):
    def __init__(
        self,
        memo: Optional[SuppressibleMessageMemo] = None,
        listeners: Optional[Iterable[MessageMediatorListener]] = None,
    ):
        self.memo: SuppressibleMessageMemo = memo if memo is not None else NbPreferencesImpl()
        self._listeners: Optional[List[MessageMediatorListener]] = list(listeners) if listeners else None

    def getSuppressibleMessageMemo(self) -> SuppressibleMessageMemo:
        return self.memo

    def _locateListeners(self) -> List[MessageMediatorListener]:
        if self._listeners is not None:
            return list(self._listeners)
        return list(_DEFAULT_LISTENERS)

    def handleMessage(self, objMessage: Message, actionID: int) -> int:
        retValue = -1
        if objMessage.isSuppressed():
            return 0
        for mandm in self._locateListeners():
            retValue = mandm.handleMessage(objMessage, actionID)
            if retValue != -1:
                break
        return retValue

    def SetClearOutputWindowOnNewSession(self, WindowTitle: str) -> None:
        for mandm in self._locateListeners():
            if isinstance(mandm, MessageMediatorSettings):
                mandm.SetClearOutputWindowOnNewSession(WindowTitle)

    def RemoveClearOutputWindowOnNewSession(self, WindowTitle: str) -> None:
        for mandm in self._locateListeners():
            if isinstance(mandm, MessageMediatorSettings):
                mandm.RemoveClearOutputWindowOnNewSession(WindowTitle)
