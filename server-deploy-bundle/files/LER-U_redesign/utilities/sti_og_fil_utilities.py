from typing import List
from dataclasses import dataclass
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType, BooleanType, BinaryType
)


# ======================================================================
# FsEntry STRUCTURE
# ======================================================================
@dataclass
class _FsEntry:
    """
    Internal representation of a file system entry.
    """
    path: str
    is_dir: bool
    length: int
    mod_time: int

    @property
    def name(self) -> str:
        return self.path.rstrip("/").split("/")[-1]


# ======================================================================
 # SPARK + HADOOP HELPERS (importable)
# ======================================================================
def _spark():
    return SparkSession.builder.getOrCreate()

def _jvm():
    return _spark()._jvm

def _conf():
    return _spark()._jsc.hadoopConfiguration()

def _mkpath(path: str):
    return _spark()._jvm.org.apache.hadoop.fs.Path(path)

def _get_fs(path: str):
    jvm = _jvm()
    conf = _conf()
    uri = jvm.java.net.URI(path)
    return jvm.org.apache.hadoop.fs.FileSystem.get(uri, conf)


# ======================================================================
# 3. FILESYSTEM FUNCTIONS 
# ======================================================================
def fs_ls(path: str) -> List[_FsEntry]:
    """
    List files and directories in a path (non-recursive).
    Equivalent to dbutils.fs.ls().
    """
    fs = _get_fs(path)
    stats = fs.listStatus(_mkpath(path))

    out: List[_FsEntry] = []
    for st in stats:
        out.append(
            _FsEntry(
                path=st.getPath().toString() + ("/" if st.isDirectory() else ""),
                is_dir=bool(st.isDirectory()),
                length=0 if st.isDirectory() else int(st.getLen()),
                mod_time=int(st.getModificationTime())
            )
        )
    return out


def fs_mkdirs(path: str) -> None:
    """
    Creates directories like dbutils.fs.mkdirs()
    """
    fs = _get_fs(path)
    fs.mkdirs(_mkpath(path))


def fs_rm(path: str, recurse: bool = False) -> None:
    """
    Delete file or directory
    Matches dbutils.fs.rm(path, recurse)
    """
    fs = _get_fs(path)
    fs.delete(_mkpath(path), bool(recurse))


def fs_exists(path: str) -> bool:
    """
    Check existence of a path.
    """
    fs = _get_fs(path)
    return fs.exists(_mkpath(path))


def fs_cp(src: str, dst: str, recurse: bool = False, overwrite: bool = False) -> None:
    """
    Copy file or directory.
    """
    jvm = _jvm()
    FileUtil = jvm.org.apache.hadoop.fs.FileUtil

    src_fs = _get_fs(src)
    dst_fs = _get_fs(dst)

    FileUtil.copy(
        src_fs, _mkpath(src),
        dst_fs, _mkpath(dst),
        bool(recurse),
        bool(overwrite),
        _conf()
    )


def fs_mv(src: str, dst: str, recurse: bool = False, overwrite: bool = False) -> None:
    """
    Move file or directory.
    Note: Hadoop FS mv ignores overwrite.
    """
    fs_cp(src, dst, recurse, overwrite)
    fs_rm(src, recurse)


def fs_read(path: str) -> str:
    """
    Read entire file contents as text.
    """
    fs = _get_fs(path)
    stream = fs.open(_mkpath(path))
    data = stream.read()
    stream.close()
    return data.decode("utf-8")


def fs_head(path: str, max_bytes: int = 65536) -> str:
    """
    Read first N bytes of a file.
    """
    fs = _get_fs(path)
    stream = fs.open(_mkpath(path))
    data = stream.read(max_bytes)
    stream.close()
    return data.decode("utf-8")


def fs_put(path: str, contents: str, overwrite: bool = True) -> None:
    """
    Write text file. Equivalent to dbutils.fs.put().
    """
    fs = _get_fs(path)
    out = fs.create(_mkpath(path), overwrite)
    out.write(bytes(contents, "utf-8"))
    out.close()


def ls_dirs(path: str) -> List[str]:
    fs = _get_fs(path)
    stats = fs.listStatus(_mkpath(path))
    return [st.getPath().toString() for st in stats if st.isDirectory()]

def ls_files(path: str) -> List[str]:
    fs = _get_fs(path)
    stats = fs.listStatus(_mkpath(path))
    return [st.getPath().toString() for st in stats if st.isFile()]

def list_all_csv_files(base_path: str, file_type: str) -> List[str]:
    fs = _get_fs(base_path)
    it = fs.listFiles(_mkpath(base_path), True)
    out = []
    while it.hasNext():
        st = it.next()
        if st.isFile():
            p = st.getPath().toString()
            if p.lower().endswith(file_type):
                out.append(p)
    return out

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