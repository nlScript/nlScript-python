from __future__ import annotations

import os
import stat
import string
import sys
from typing import List, cast


class CompletePath:

    _filesystemCache = {}

    def __init__(self):
        pass

    @staticmethod
    def clearFilesystemCache() -> None:
        CompletePath._filesystemCache.clear()

    @staticmethod
    def getParent(alreadyEntered: str) -> str or None:
        if not os.path.isabs(alreadyEntered):
            return None
        if len(alreadyEntered) == 0:
            return None
        return os.path.dirname(alreadyEntered)

    @staticmethod
    def getDrives() -> List[str]:
        return ['%s:' % d for d in string.ascii_uppercase if os.path.exists('%s:' % d)]

    @staticmethod
    def getRootDirectories():
        if sys.platform.startswith("win32"):  # TODO cygwin?
            return CompletePath.getDrives()
        else:
            return "/"

    @staticmethod
    def getChild(alreadyEntered: str) -> str:
        parent = CompletePath.getParent(alreadyEntered)
        if parent is None:
            return alreadyEntered
        if os.path.samefile(parent, alreadyEntered):
            return ""
        rel = os.path.relpath(alreadyEntered, parent)
        return rel

    @staticmethod
    def getFileName(path: str) -> str:
        return path if not os.path.isabs(path) else os.path.basename(path)

    @staticmethod
    def isHidden(path: str) -> bool:
        return CompletePath.getFileName(path).startswith(".") or\
            bool(os.stat(path).st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)

    @staticmethod
    def getSiblings(alreadyEntered: str) -> List[str]:
        print("getSiblings(" + alreadyEntered + ")")
        parent = CompletePath.getParent(alreadyEntered)
        child = CompletePath.getChild(alreadyEntered)

        # siblingsArray: List[str] or None = None

        if parent in CompletePath._filesystemCache.keys():
            siblingsArray = CompletePath._filesystemCache.get(parent)
        else:
            siblingsArray = list(map(lambda x: CompletePath.addSeparator(parent) + x, os.listdir(parent))) if parent is not None else CompletePath.getRootDirectories()
            CompletePath._filesystemCache[parent] = siblingsArray

        tmp = filter(lambda x: CompletePath.getFileName(x).lower().startswith(child.lower()), siblingsArray)
        tmp = sorted(map(lambda x: PathWrapper(x), tmp))
        # tmp = map(lambda x: x.path + os.path.sep if x.isDirectory and not x.path.endswith(os.path.sep) else x.path, tmp)
        tmp = map(lambda x: CompletePath.addSeparator(x.path) if x.isDirectory else x.path, tmp)
        return list(tmp)

    @staticmethod
    def addSeparator(path: str) -> str:
        return path if path.endswith(os.path.sep) else path + os.path.sep

    @staticmethod
    def getCompletion(alreadyEntered: str) -> str:
        siblings = CompletePath.getSiblings(alreadyEntered)
        return alreadyEntered if len(siblings) == 0 else ";;;".join(siblings)


class PathWrapper:
    def __init__(self, path: str):
        self.path = path
        self.name = CompletePath.getFileName(path)
        self.isHidden = CompletePath.isHidden(path)
        self.isDirectory = os.path.isdir(path)

    def __lt__(self, other):
        o = cast(PathWrapper, other)
        if self.isHidden and not o.isHidden:
            return False
        if o.isHidden and not self.isHidden:
            return True
        if self.isDirectory and not o.isDirectory:
            return True
        if o.isDirectory and not self.isDirectory:
            return False
        return self.name < other.name
