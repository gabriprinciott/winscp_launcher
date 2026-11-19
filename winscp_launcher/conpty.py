"""Windows ConPTY terminal controller."""

import ctypes
import os
import re
import subprocess
import threading
from ctypes import wintypes

from .config import BASE_DIR
from .logging_config import log

if os.name == "nt":
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
    HANDLE = wintypes.HANDLE
    DWORD = wintypes.DWORD
    BOOL = wintypes.BOOL
    WORD = wintypes.WORD
    ULONG_PTR = ctypes.c_size_t

    STD_INPUT_HANDLE = -10
    STD_OUTPUT_HANDLE = -11
    ENABLE_PROCESSED_INPUT = 0x0001
    ENABLE_LINE_INPUT = 0x0002
    ENABLE_ECHO_INPUT = 0x0004
    ENABLE_MOUSE_INPUT = 0x0010
    ENABLE_QUICK_EDIT_MODE = 0x0040
    ENABLE_EXTENDED_FLAGS = 0x0080
    ENABLE_VIRTUAL_TERMINAL_INPUT = 0x0200
    ENABLE_PROCESSED_OUTPUT = 0x0001
    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
    DISABLE_NEWLINE_AUTO_RETURN = 0x0008
    HANDLE_FLAG_INHERIT = 0x00000001
    EXTENDED_STARTUPINFO_PRESENT = 0x00080000
    PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
    WAIT_OBJECT_0 = 0x00000000
    WAIT_TIMEOUT = 0x00000102
    WAIT_FAILED = 0xFFFFFFFF
    ERROR_BROKEN_PIPE = 109
    ERROR_HANDLE_EOF = 38

    class COORD(ctypes.Structure):
        _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

    class SMALL_RECT(ctypes.Structure):
        _fields_ = [
            ("Left", ctypes.c_short),
            ("Top", ctypes.c_short),
            ("Right", ctypes.c_short),
            ("Bottom", ctypes.c_short),
        ]

    class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
        _fields_ = [
            ("dwSize", COORD),
            ("dwCursorPosition", COORD),
            ("wAttributes", WORD),
            ("srWindow", SMALL_RECT),
            ("dwMaximumWindowSize", COORD),
        ]

    class SECURITY_ATTRIBUTES(ctypes.Structure):
        _fields_ = [
            ("nLength", DWORD),
            ("lpSecurityDescriptor", ctypes.c_void_p),
            ("bInheritHandle", BOOL),
        ]

    class STARTUPINFOW(ctypes.Structure):
        _fields_ = [
            ("cb", DWORD),
            ("lpReserved", wintypes.LPWSTR),
            ("lpDesktop", wintypes.LPWSTR),
            ("lpTitle", wintypes.LPWSTR),
            ("dwX", DWORD),
            ("dwY", DWORD),
            ("dwXSize", DWORD),
            ("dwYSize", DWORD),
            ("dwXCountChars", DWORD),
            ("dwYCountChars", DWORD),
            ("dwFillAttribute", DWORD),
            ("dwFlags", DWORD),
            ("wShowWindow", WORD),
            ("cbReserved2", WORD),
            ("lpReserved2", ctypes.POINTER(ctypes.c_byte)),
            ("hStdInput", HANDLE),
            ("hStdOutput", HANDLE),
            ("hStdError", HANDLE),
        ]

    class STARTUPINFOEXW(ctypes.Structure):
        _fields_ = [
            ("StartupInfo", STARTUPINFOW),
            ("lpAttributeList", ctypes.c_void_p),
        ]

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("hProcess", HANDLE),
            ("hThread", HANDLE),
            ("dwProcessId", DWORD),
            ("dwThreadId", DWORD),
        ]

    kernel32.GetStdHandle.argtypes = [ctypes.c_int]
    kernel32.GetStdHandle.restype = HANDLE
    kernel32.GetConsoleMode.argtypes = [HANDLE, ctypes.POINTER(DWORD)]
    kernel32.GetConsoleMode.restype = BOOL
    kernel32.SetConsoleMode.argtypes = [HANDLE, DWORD]
    kernel32.SetConsoleMode.restype = BOOL
    kernel32.GetConsoleScreenBufferInfo.argtypes = [
        HANDLE,
        ctypes.POINTER(CONSOLE_SCREEN_BUFFER_INFO),
    ]
    kernel32.GetConsoleScreenBufferInfo.restype = BOOL
    kernel32.SetHandleInformation.argtypes = [HANDLE, DWORD, DWORD]
    kernel32.SetHandleInformation.restype = BOOL
    kernel32.CreatePipe.argtypes = [
        ctypes.POINTER(HANDLE),
        ctypes.POINTER(HANDLE),
        ctypes.POINTER(SECURITY_ATTRIBUTES),
        DWORD,
    ]
    kernel32.CreatePipe.restype = BOOL
    kernel32.CloseHandle.argtypes = [HANDLE]
    kernel32.CloseHandle.restype = BOOL
    kernel32.CreatePseudoConsole.argtypes = [COORD, HANDLE, HANDLE, DWORD, ctypes.POINTER(HANDLE)]
    kernel32.CreatePseudoConsole.restype = ctypes.c_long
    kernel32.ClosePseudoConsole.argtypes = [HANDLE]
    kernel32.ResizePseudoConsole.argtypes = [HANDLE, COORD]
    kernel32.ResizePseudoConsole.restype = ctypes.c_long
    kernel32.InitializeProcThreadAttributeList.argtypes = [
        ctypes.c_void_p,
        DWORD,
        DWORD,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    kernel32.InitializeProcThreadAttributeList.restype = BOOL
    kernel32.UpdateProcThreadAttribute.argtypes = [
        ctypes.c_void_p,
        DWORD,
        ULONG_PTR,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    kernel32.UpdateProcThreadAttribute.restype = BOOL
    kernel32.DeleteProcThreadAttributeList.argtypes = [ctypes.c_void_p]
    kernel32.CreateProcessW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        ctypes.c_void_p,
        ctypes.c_void_p,
        BOOL,
        DWORD,
        ctypes.c_void_p,
        wintypes.LPCWSTR,
        ctypes.POINTER(STARTUPINFOEXW),
        ctypes.POINTER(PROCESS_INFORMATION),
    ]
    kernel32.CreateProcessW.restype = BOOL
    kernel32.ReadFile.argtypes = [
        HANDLE,
        ctypes.c_void_p,
        DWORD,
        ctypes.POINTER(DWORD),
        ctypes.c_void_p,
    ]
    kernel32.ReadFile.restype = BOOL
    kernel32.WriteFile.argtypes = [
        HANDLE,
        ctypes.c_void_p,
        DWORD,
        ctypes.POINTER(DWORD),
        ctypes.c_void_p,
    ]
    kernel32.WriteFile.restype = BOOL
    kernel32.WaitForMultipleObjects.argtypes = [DWORD, ctypes.POINTER(HANDLE), BOOL, DWORD]
    kernel32.WaitForMultipleObjects.restype = DWORD
    kernel32.WaitForSingleObject.argtypes = [HANDLE, DWORD]
    kernel32.WaitForSingleObject.restype = DWORD
    kernel32.TerminateProcess.argtypes = [HANDLE, wintypes.UINT]
    kernel32.GetExitCodeProcess.argtypes = [HANDLE, ctypes.POINTER(DWORD)]
    kernel32.SetConsoleOutputCP.argtypes = [wintypes.UINT]


def win_error(message):
    error = ctypes.get_last_error()
    return OSError(error, f"{message}: {ctypes.FormatError(error).strip()}")


def _write_all(handle, data):
    offset = 0
    while offset < len(data):
        chunk = data[offset:]
        buffer = ctypes.create_string_buffer(chunk)
        written = DWORD(0)
        if not kernel32.WriteFile(handle, buffer, len(chunk), ctypes.byref(written), None):
            raise win_error("WriteFile failed")
        if written.value == 0:
            raise BrokenPipeError("WriteFile wrote zero bytes")
        offset += written.value


def _console_size(output_handle):
    info = CONSOLE_SCREEN_BUFFER_INFO()
    if not kernel32.GetConsoleScreenBufferInfo(output_handle, ctypes.byref(info)):
        return 120, 30
    return (
        max(20, info.srWindow.Right - info.srWindow.Left + 1),
        max(5, info.srWindow.Bottom - info.srWindow.Top + 1),
    )


ANSI_SEQUENCE_RE = re.compile(rb"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
VT_MOUSE_INPUT_RE = re.compile(rb"\x1b\[<\d+;\d+;\d+[Mm]")


class PromptDetector:
    def __init__(self, pattern, on_match):
        self.regex = re.compile(pattern)
        self.on_match = on_match
        self.line = bytearray()
        self.line_reported = False
        self.line_number = 0

    def feed(self, data):
        for byte in data:
            if byte in (10, 13):
                self._check()
                if self.line:
                    self.line_number += 1
                self.line.clear()
                self.line_reported = False
            elif byte in (8, 127):
                if self.line:
                    self.line.pop()
            else:
                self.line.append(byte)
            self._check()

    def _check(self):
        if not self.line or self.line_reported:
            return
        clean = ANSI_SEQUENCE_RE.sub(b"", bytes(self.line))
        text = clean.decode("utf-8", errors="replace").strip()
        if self.regex.fullmatch(text):
            self.line_reported = True
            log.info("Detected prompt on line %d: %r", self.line_number + 1, text[:300])
            self.on_match()


class ConPTYSession:
    def __init__(self, command, startup_commands, prompt_regex):
        if os.name != "nt":
            raise RuntimeError("The ConPTY controller only runs on Windows")
        self.command = command
        self.startup_commands = startup_commands or []
        self.prompt_regex = prompt_regex
        self.hpc = HANDLE()
        self.h_input_write = HANDLE()
        self.h_output_read = HANDLE()
        self.process = PROCESS_INFORMATION()
        self.stdin_handle = kernel32.GetStdHandle(STD_INPUT_HANDLE)
        self.stdout_handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        self.old_input_mode = DWORD()
        self.old_output_mode = DWORD()
        self.input_mode_changed = False
        self.output_mode_changed = False
        self.write_lock = threading.Lock()
        self.startup_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.output_thread = None
        self.resize_thread = None
        self.startup_index = 0

    def _write_pty(self, data):
        with self.write_lock:
            _write_all(self.h_input_write, data)

    def _send_next_startup_command(self):
        with self.startup_lock:
            if self.startup_index >= len(self.startup_commands):
                return
            command = self.startup_commands[self.startup_index]
            self.startup_index += 1
        command = command.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r")
        log.info("Startup command %d/%d sent", self.startup_index, len(self.startup_commands))
        self._write_pty(command.encode("utf-8") + b"\r")

    def _read_output(self):
        detector = PromptDetector(self.prompt_regex, self._send_next_startup_command)
        buffer = ctypes.create_string_buffer(8192)
        while not self.stop_event.is_set():
            read = DWORD(0)
            if not kernel32.ReadFile(
                self.h_output_read, buffer, len(buffer), ctypes.byref(read), None
            ):
                error = ctypes.get_last_error()
                if error not in (ERROR_BROKEN_PIPE, ERROR_HANDLE_EOF):
                    log.error("ConPTY output ReadFile failed error=%s", error)
                break
            if read.value == 0:
                break
            data = buffer.raw[: read.value]
            try:
                _write_all(self.stdout_handle, data)
            except Exception as exc:
                log.error("Could not write terminal output: %s", exc)
                self.stop_event.set()
                break
            detector.feed(data)

    def _watch_resize(self):
        last_size = None
        while not self.stop_event.wait(0.25):
            size = _console_size(self.stdout_handle)
            if size != last_size:
                result = kernel32.ResizePseudoConsole(self.hpc, COORD(*size))
                if result != 0:
                    log.error("ResizePseudoConsole HRESULT=0x%08X", result & 0xFFFFFFFF)
                last_size = size

    def _create_pipe(self):
        security = SECURITY_ATTRIBUTES()
        security.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)
        security.bInheritHandle = True
        read_handle, write_handle = HANDLE(), HANDLE()
        if not kernel32.CreatePipe(
            ctypes.byref(read_handle), ctypes.byref(write_handle), ctypes.byref(security), 0
        ):
            raise win_error("CreatePipe failed")
        return read_handle, write_handle

    def _start_child(self):
        h_input_read, self.h_input_write = self._create_pipe()
        self.h_output_read, h_output_write = self._create_pipe()
        for handle, label in ((self.h_input_write, "input"), (self.h_output_read, "output")):
            if not kernel32.SetHandleInformation(handle, HANDLE_FLAG_INHERIT, 0):
                raise win_error(f"SetHandleInformation({label}) failed")

        width, height = _console_size(self.stdout_handle)
        result = kernel32.CreatePseudoConsole(
            COORD(width, height), h_input_read, h_output_write, 0, ctypes.byref(self.hpc)
        )
        kernel32.CloseHandle(h_input_read)
        kernel32.CloseHandle(h_output_write)
        if result != 0:
            raise OSError(f"CreatePseudoConsole failed: HRESULT 0x{result & 0xFFFFFFFF:08X}")

        attribute_size = ctypes.c_size_t(0)
        kernel32.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(attribute_size))
        attribute_buffer = ctypes.create_string_buffer(attribute_size.value)
        attribute_list = ctypes.cast(attribute_buffer, ctypes.c_void_p)
        if not kernel32.InitializeProcThreadAttributeList(
            attribute_list, 1, 0, ctypes.byref(attribute_size)
        ):
            raise win_error("InitializeProcThreadAttributeList failed")
        try:
            if not kernel32.UpdateProcThreadAttribute(
                attribute_list,
                0,
                PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,
                ctypes.c_void_p(self.hpc.value),
                ctypes.sizeof(HANDLE),
                None,
                None,
            ):
                raise win_error("UpdateProcThreadAttribute failed")
            startup = STARTUPINFOEXW()
            startup.StartupInfo.cb = ctypes.sizeof(STARTUPINFOEXW)
            startup.lpAttributeList = attribute_list
            process_info = PROCESS_INFORMATION()
            command_line = ctypes.create_unicode_buffer(subprocess.list2cmdline(self.command))
            if not kernel32.CreateProcessW(
                None,
                command_line,
                None,
                None,
                True,
                EXTENDED_STARTUPINFO_PRESENT,
                None,
                str(BASE_DIR),
                ctypes.byref(startup),
                ctypes.byref(process_info),
            ):
                raise win_error("CreateProcessW for WSL failed")
            self.process = process_info
            log.info("ConPTY child started pid=%s", self.process.dwProcessId)
        finally:
            kernel32.DeleteProcThreadAttributeList(attribute_list)

    def _configure_outer_terminal(self):
        if not kernel32.GetConsoleMode(self.stdin_handle, ctypes.byref(self.old_input_mode)):
            raise win_error("GetConsoleMode(stdin) failed")
        if not kernel32.GetConsoleMode(self.stdout_handle, ctypes.byref(self.old_output_mode)):
            raise win_error("GetConsoleMode(stdout) failed")
        input_mode = (
            self.old_input_mode.value | ENABLE_VIRTUAL_TERMINAL_INPUT | ENABLE_EXTENDED_FLAGS
        )
        input_mode &= ~(
            ENABLE_PROCESSED_INPUT
            | ENABLE_LINE_INPUT
            | ENABLE_ECHO_INPUT
            | ENABLE_MOUSE_INPUT
            | ENABLE_QUICK_EDIT_MODE
        )
        if not kernel32.SetConsoleMode(self.stdin_handle, input_mode):
            raise win_error("SetConsoleMode(stdin) failed")
        self.input_mode_changed = True
        output_mode = (
            self.old_output_mode.value
            | ENABLE_PROCESSED_OUTPUT
            | ENABLE_VIRTUAL_TERMINAL_PROCESSING
            | DISABLE_NEWLINE_AUTO_RETURN
        )
        if not kernel32.SetConsoleMode(self.stdout_handle, output_mode):
            raise win_error("SetConsoleMode(stdout) failed")
        self.output_mode_changed = True
        kernel32.SetConsoleOutputCP(65001)

    def _restore_outer_terminal(self):
        if self.input_mode_changed:
            kernel32.SetConsoleMode(self.stdin_handle, self.old_input_mode.value)
        if self.output_mode_changed:
            kernel32.SetConsoleMode(self.stdout_handle, self.old_output_mode.value)

    def _close_resources(self):
        if (
            self.process.hProcess
            and kernel32.WaitForSingleObject(self.process.hProcess, 0) != WAIT_OBJECT_0
        ):
            kernel32.TerminateProcess(self.process.hProcess, 1)
            kernel32.WaitForSingleObject(self.process.hProcess, 1000)
        if self.output_thread and self.output_thread.is_alive():
            kernel32.CloseHandle(self.h_output_read)
            self.output_thread.join(timeout=1.0)
        if self.resize_thread:
            self.resize_thread.join(timeout=0.5)
        self._restore_outer_terminal()
        if self.hpc:
            kernel32.ClosePseudoConsole(self.hpc)
        for handle in (
            self.h_input_write,
            self.h_output_read,
            self.process.hThread,
            self.process.hProcess,
        ):
            if handle:
                kernel32.CloseHandle(handle)

    def run(self):
        self._configure_outer_terminal()
        try:
            self._start_child()
            self.output_thread = threading.Thread(
                target=self._read_output, name="conpty-output", daemon=True
            )
            self.output_thread.start()
            self.resize_thread = threading.Thread(
                target=self._watch_resize, name="conpty-resize", daemon=True
            )
            self.resize_thread.start()
            handles = (HANDLE * 2)(self.process.hProcess, self.stdin_handle)
            while not self.stop_event.is_set():
                result = kernel32.WaitForMultipleObjects(2, handles, False, 100)
                if result == WAIT_OBJECT_0:
                    break
                if result == WAIT_OBJECT_0 + 1:
                    buffer, read = ctypes.create_string_buffer(4096), DWORD(0)
                    if not kernel32.ReadFile(
                        self.stdin_handle, buffer, len(buffer), ctypes.byref(read), None
                    ):
                        log.error(
                            "Terminal input ReadFile failed error=%s", ctypes.get_last_error()
                        )
                        break
                    if read.value:
                        data = VT_MOUSE_INPUT_RE.sub(b"", buffer.raw[: read.value])
                        if data:
                            self._write_pty(data)
                elif result == WAIT_FAILED:
                    raise win_error("WaitForMultipleObjects failed")
            self.stop_event.set()
            kernel32.WaitForSingleObject(self.process.hProcess, 3000)
            exit_code = DWORD(0)
            kernel32.GetExitCodeProcess(self.process.hProcess, ctypes.byref(exit_code))
            return int(exit_code.value)
        finally:
            self.stop_event.set()
            self._close_resources()
