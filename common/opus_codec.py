import ctypes
import ctypes.util
import os
import sys

OPUS_IMPORT_ERROR = None
opuslib = None


def get_dll_path():
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "libopus.dll")

    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "libopus.dll"))


def _configure_opus_loader():
    dll_path = get_dll_path()
    if not os.path.exists(dll_path):
        return dll_path

    dll_dir = os.path.dirname(dll_path)

    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(dll_dir)

    path_parts = os.environ.get("PATH", "").split(os.pathsep)
    if dll_dir not in path_parts:
        os.environ["PATH"] = dll_dir + os.pathsep + os.environ.get("PATH", "")

    original_find_library = ctypes.util.find_library

    def _find_library(name):
        if name == "opus":
            return dll_path
        return original_find_library(name)

    ctypes.util.find_library = _find_library
    ctypes.CDLL(dll_path)
    return dll_path


DLL_PATH = _configure_opus_loader()

try:
    import opuslib
except Exception as exc:
    OPUS_IMPORT_ERROR = exc


class OpusCodec:
    def __init__(self, rate=48000, channels=1):
        if opuslib is None:
            detail = f" {OPUS_IMPORT_ERROR}" if OPUS_IMPORT_ERROR else ""
            raise RuntimeError(f"Install and configure Opus support to enable voice chat.{detail}")

        self.encoder = opuslib.Encoder(rate, channels, opuslib.APPLICATION_AUDIO)
        self.decoder = opuslib.Decoder(rate, channels)

    def encode(self, pcm):
        return self.encoder.encode(pcm, 960)

    def decode(self, data):
        return self.decoder.decode(data, 960)
