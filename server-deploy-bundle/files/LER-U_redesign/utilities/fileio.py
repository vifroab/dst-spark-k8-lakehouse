def s3a_copy_file(spark, src_uri: str, tgt_uri: str, overwrite: bool = True):
    """
    Kopiér en enkelt fil as-is fra src_uri til tgt_uri.
    Sletter destinationen først, hvis den findes.
    Logger filstørrelsen efter kopien.
    """
    sc   = spark.sparkContext
    jvm  = sc._jvm
    conf = sc._jsc.hadoopConfiguration()

    Path    = jvm.org.apache.hadoop.fs.Path
    IOUtils = jvm.org.apache.hadoop.io.IOUtils

    src_path = Path(src_uri)
    tgt_path = Path(tgt_uri)

    fs_src = jvm.org.apache.hadoop.fs.FileSystem.get(jvm.java.net.URI(src_uri), conf)
    fs_tgt = jvm.org.apache.hadoop.fs.FileSystem.get(jvm.java.net.URI(tgt_uri), conf)

    # Slet destinationen først, hvis den findes
    if fs_tgt.exists(tgt_path):
        if overwrite:
            fs_tgt.delete(tgt_path, True)
            print(f"Slettede eksisterende destination: {tgt_path.toString()}")
        else:
            raise FileExistsError(f"Destination findes allerede: {tgt_path.toString()}")

    # Kopiér via streams (robust på S3A/MinIO)
    in_stream  = fs_src.open(src_path)
    out_stream = fs_tgt.create(tgt_path, overwrite)
    IOUtils.copyBytes(in_stream, out_stream, conf, True)

    # Verificér at filen nu har korrekt længde
    status = fs_tgt.getFileStatus(tgt_path)
    print(f"Kopieret {src_uri} -> {tgt_uri}, størrelse={status.getLen()} bytes")

    return tgt_path.toString()
