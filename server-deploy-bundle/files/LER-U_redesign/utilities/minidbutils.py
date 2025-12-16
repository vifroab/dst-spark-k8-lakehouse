# minidbutils.py
from typing import List

class _FsEntry(dict):
    """Lille hjælpestruktur så du kan bruge .path, .name, .size som i Databricks."""
    @property
    def path(self): return self["path"]
    @property
    def name(self): return self["name"]
    @property
    def size(self): return self["size"]
    @property
    def modificationTime(self): return self["modificationTime"]
    @property
    def isDir(self): return self["isDir"]


class DBUtilsFs:
    """
    Minimal klon af Databricks' dbutils.fs — virker på file:// og s3a://
    Funktioner:
      - ls(path)
      - mkdirs(path)
      - rm(path, recurse=False)
      - cp(src, dst, recurse=False, overwrite=False)
      - mv(src, dst, recurse=False, overwrite=False)
      - head(path, maxBytes=65536)
      - read(path)
      - put(path, contents, overwrite=True)
      - exists(path)
    """
    def __init__(self, spark):
        self.spark = spark
        self._jvm = spark._jvm
        self._jsc = spark._jsc
        self._hconf = self._jsc.hadoopConfiguration()
        self._FileSystem = self._jvm.org.apache.hadoop.fs.FileSystem
        self._FileUtil = self._jvm.org.apache.hadoop.fs.FileUtil
        self._Path = self._jvm.org.apache.hadoop.fs.Path
        self._URI = self._jvm.java.net.URI
        self._IOUtils = self._jvm.org.apache.commons.io.IOUtils

    def _get_fs(self, uri_str: str):
        return self._FileSystem.get(self._URI(uri_str), self._hconf)

    def _mkpath(self, p: str):
        return self._Path(p)

    # -------- public API --------

    def ls(self, path: str) -> List[_FsEntry]:
        fs = self._get_fs(path)
        stats = fs.listStatus(self._mkpath(path))
        out = []
        for st in stats:
            p = st.getPath().toString()
            name = st.getPath().getName()
            is_dir = st.isDirectory()
            size = st.getLen() if not is_dir else 0
            mtime = st.getModificationTime()
            out.append(_FsEntry({
                "path": p + ("/" if is_dir and not p.endswith("/") else ""),
                "name": name + ("/" if is_dir and not name.endswith("/") else ""),
                "size": int(size),
                "modificationTime": int(mtime),
                "isDir": bool(is_dir)
            }))
        return out

    def mkdirs(self, path: str) -> None:
        fs = self._get_fs(path)
        fs.mkdirs(self._mkpath(path))

    def rm(self, path: str, recurse: bool = False) -> None:
        fs = self._get_fs(path)
        fs.delete(self._mkpath(path), bool(recurse))

    def cp(self, src: str, dst: str, recurse: bool = False, overwrite: bool = False) -> None:
        fs_src = self._get_fs(src)
        fs_dst = self._get_fs(dst)
        p_src = self._mkpath(src)
        p_dst = self._mkpath(dst)

        if fs_src.isFile(p_src):
            if overwrite and fs_dst.exists(p_dst):
                fs_dst.delete(p_dst, False)
            if not self._FileUtil.copy(fs_src, p_src, fs_dst, p_dst, False, overwrite, self._hconf):
                raise IOError(f"copy failed: {src} -> {dst}")
        else:
            if not recurse:
                raise ValueError("cp: src er en mappe – brug recurse=True")
            it = fs_src.listFiles(p_src, True)
            base = p_src.toString().rstrip("/") + "/"
            while it.hasNext():
                st = it.next()
                if st.isFile():
                    rel = st.getPath().toString().replace(base, "", 1)
                    target = self._mkpath((dst.rstrip("/") + "/" + rel))
                    parent = target.getParent()
                    fs_dst.mkdirs(parent)
                    if overwrite and fs_dst.exists(target):
                        fs_dst.delete(target, False)
                    if not self._FileUtil.copy(fs_src, st.getPath(), fs_dst, target, False, overwrite, self._hconf):
                        raise IOError(f"copy failed: {st.getPath()} -> {target}")

    def mv(self, src: str, dst: str, recurse: bool = False, overwrite: bool = False) -> None:
        fs_src = self._get_fs(src)
        fs_dst = self._get_fs(dst)
        p_src = self._mkpath(src)
        p_dst = self._mkpath(dst)

        if overwrite and fs_dst.exists(p_dst):
            fs_dst.delete(p_dst, True)

        if fs_src.rename(p_src, p_dst):
            return

        # fallback: copy + delete
        self.cp(src, dst, recurse=recurse, overwrite=True)
        fs_src.delete(p_src, True)

    def head(self, path: str, maxBytes: int = 65536) -> str:
        fs = self._get_fs(path)
        p = self._mkpath(path)
        if not fs.exists(p) or not fs.isFile(p):
            raise FileNotFoundError(path)
        stream = fs.open(p)
        try:
            buf = self._jvm.java.io.ByteArrayOutputStream()
            self._IOUtils.copyLarge(stream, buf, 0, max(0, int(maxBytes)))
            return bytes(buf.toByteArray()).decode("utf-8", errors="replace")
        finally:
            stream.close()

    def read(self, path: str) -> str:
        fs = self._get_fs(path)
        p = self._mkpath(path)
        if not fs.exists(p) or not fs.isFile(p):
            raise FileNotFoundError(path)
        stream = fs.open(p)
        try:
            data = self._IOUtils.toByteArray(stream)
            return bytes(data).decode("utf-8", errors="replace")
        finally:
            stream.close()

    def put(self, path: str, contents: str, overwrite: bool = True, encoding: str = "utf-8") -> None:
        fs = self._get_fs(path)
        p = self._mkpath(path)
        parent = p.getParent()
        if parent is not None:
            fs.mkdirs(parent)
        if not overwrite and fs.exists(p):
            raise FileExistsError(f"{path} exists and overwrite=False")
        out = fs.create(p, bool(overwrite))
        try:
            data = contents.encode(encoding)
            out.write(data)
            out.hflush()
        finally:
            out.close()

    def exists(self, path: str) -> bool:
        fs = self._get_fs(path)
        return bool(fs.exists(self._mkpath(path)))


class MiniDBUtils:
    """Wrapper, så du kan bruge dbutils.fs.* ligesom i Databricks."""
    def __init__(self, spark):
        self.fs = DBUtilsFs(spark)


def get_dbutils(spark) -> MiniDBUtils:
    """Convenience factory – brug: dbutils = get_dbutils(spark)"""
    return MiniDBUtils(spark)
