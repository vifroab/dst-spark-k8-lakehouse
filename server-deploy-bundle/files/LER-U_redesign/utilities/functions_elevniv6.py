from pyspark.sql import functions as F
from pyspark.sql import SparkSession
from pyspark.sql.utils import AnalysisException
from delta.tables import DeltaTable
from datetime import datetime
import posixpath

#get spark session
def _get_spark():
    s = SparkSession.getActiveSession()
    if s is None:
        raise RuntimeError("no active SparkSession found")
    return s


#loop thorugh columns and rename
def _normalize(df, renames: dict):
    for src, destination in (renames or {}).items():
        if src in df.columns and destination not in df.columns:
            df = df.withColumnRenamed(src, destination)
    return df


def _validate(df, required_cols: list[str]):
    #checks if dataset is empty
    if df.rdd.isEmpty():
        raise ValueError("input dataset is empty")
    #looks for the required columns if missing, throws an error
    missing = [c for c in (required_cols or []) if c not in df.columns]
    if missing:
        raise ValueError(f"these required columns are missing: {missing}")

#add out metadata
def _add_meta(df, delivery_id: str, source_system: str):
    return (df
        .withColumn("source_system", F.lit(source_system))
        .withColumn("delivery_id",   F.lit(delivery_id))
        .withColumn("ingestion_ts",  F.current_timestamp())
        .withColumn("ingest_dt",     F.to_date(F.current_timestamp()))
    )

#checks if table exists
def _delta_exists(path: str) -> bool:
    try:
        s = _get_spark()
        return DeltaTable.isDeltaTable(s, path)
    except Exception:
        return False

#auto generate delivery id if user specifies it
def _auto_delivery_id(input_path: str, source_system: str) -> str:
    #takes the file name and replace . with _
    base = posixpath.basename(input_path).replace(".", "_")
    #takes the datetime
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    #build the id by using source_system, file name and timestamp
    return f"{source_system.lower()}_{base}_{ts}"

#get a source fingerprint to ceck if the same file already has been appended
def _source_fingerprint(input_path: str) -> str:
    s = _get_spark()
    #get spark jvm
    jvm = s._jvm
    #hadoop config (used to talk to the filesystem)
    hconf = s.sparkContext._jsc.hadoopConfiguration()
    #wrap path as hadoop path
    p = jvm.org.apache.hadoop.fs.Path(input_path)
    #get the right filesystem implimentation for the specific path (in our case s3a://)
    fs = p.getFileSystem(hconf)
    #get file metadata
    status = fs.getFileStatus(p)
    #returns the path, file size and modification time
    return f"{input_path}:{status.getLen()}:{status.getModificationTime()}"


def _validate_issues(dfw, delta_path, delivery_id, fp, force_reload):
    #initilize and empty list for potential issues
    issues = []
    #only run our validatoin if a delta table already exists
    if _delta_exists(delta_path):
        #get a spark session
        s = _get_spark()
        #load our delta table
        dt_df = DeltaTable.forPath(s, delta_path).toDF()
        #get the current and new column name
        base_cols = dt_df.columns
        new_cols  = dfw.columns
        #capture the extra and missing columns from the new dataset
        base_set = {c for c in base_cols if c != "source_fingerprint"}
        new_set  = {c for c in new_cols  if c != "source_fingerprint"}
        missing = [c for c in base_cols if c != "source_fingerprint" and c not in new_set]
        extra   = [c for c in new_cols  if c != "source_fingerprint" and c not in base_set]
        #append the missing or extra columns to issues
        if missing or extra:
            issues.append(f"extra or missing columns found: missing: {missing} ; extra: {extra}")
        #checks if there is any delivery id with the same name
        if dt_df.filter(F.col("delivery_id") == delivery_id).limit(1).count() > 0:
            #append if there is a duplicate delivery id
            issues.append(f"duplicate delivery_id: '{delivery_id}' already exists")
        #check if source finger print already exists. If it does append to issues
        if "source_fingerprint" in dt_df.columns:
            if dt_df.filter(F.col("source_fingerprint") == fp).limit(1).count() > 0:
                issues.append("the exact same delivery file has already been ingested (same path/size/modification time)")
    return issues

#print the issues (only if list is not empty)
def _print_report(issues):
    if issues:
        print("validation report:")
        for m in issues:
            print(" -", m)


def _gate_write(issues, force_schema, force_reload, dry_run):
    #if your only in validatoin mode(dry_run), skip any write. (validation mode alway skip any write)
    if dry_run:
        return {"ok": False, "skipped": True, "issues": issues, "reason": "dry_run=True"}
    #check if their is any schema issues (missing or extra columns found)
    has_schema = any("schema differences detected" in i for i in issues)
    #checks if the delivery id or source fingerprint is the same
    has_dupes  = any(i.startswith("duplicate delivery_id") or "already been ingested" in i for i in issues)
    ## if force schema is set to false do not write, if it is set to True allow to write even though there is schema issues
    if has_schema and not force_schema:
        return {"ok": False, "skipped": True, "issues": issues, "reason": "schema mismatch and force_schema=False"}
    #if force reload is set to false do not write, if it is set to True allow to write even though the same id or source fingerprint exists
    if has_dupes and not force_reload:
        return {"ok": False, "skipped": True, "issues": issues, "reason": "duplicate detected and force_reload=False"}
    #no blocking conditions (allow to write)
    return None


def ingest_single_path(
    input_path: str,
    delta_path: str,
    source_system: str,
    delivery_id: str | None,
    required_cols: list[str],
    renames: dict,
    force_reload: bool,
    force_schema: bool = False,
    dry_run: bool = False
):

    #load the new delivery
    try:
        s = _get_spark()
        df = s.read.option("header", True).csv(input_path)
    except AnalysisException as e:
        raise RuntimeError(f"failed to read the csv at {input_path}: {e.desc}")
    #normilize and validate
    df = _normalize(df, renames)
    _validate(df, required_cols)

    #use the user defined id or use the auto generated one
    delivery_id = delivery_id or _auto_delivery_id(input_path, source_system)

    #computa source fingerprint and add meta data
    fp = _source_fingerprint(input_path)
    dfw = _add_meta(df, delivery_id, source_system).withColumn("source_fingerprint", F.lit(fp))

    #checks if the delta table already exists
    exists = _delta_exists(delta_path)

    #run all of the pre write chechks
    issues = _validate_issues(dfw, delta_path, delivery_id, fp, force_reload)
    #print our validation report
    _print_report(issues)
    #decide weather to skip or to write depending on issues and configuration
    res = _gate_write(issues, force_schema, force_reload, dry_run)
    #if res is none the function will continue to the write phase
    if res:
        return res

    #makes a delta writer and partition by ingest_dt
    writer = dfw.write.format("delta").partitionBy("delivery_id", "ingest_dt")
    
    #check if delta table already exists and check if source_fingerprint exists. if the table does not have a source fingerprint yet allow writer option merge schema. This allows us to add new columns (source fingerprint) witout failing
    if exists:
        if "source_fingerprint" not in DeltaTable.forPath(s, delta_path).toDF().columns or any("schema differences detected" in i for i in issues):
            writer = writer.option("mergeSchema", "true")
        #using append because the table already exists
        writer.mode("append").save(delta_path)
        #print confirmation
        print(f"appended '{delivery_id}' to {delta_path}")
    else:
    #if the delta table does not already exist use overwrite instead and create a new table
        writer.mode("overwrite").option("overwriteSchema", "true").save(delta_path)
        #print confirmation
        print(f"no table existed so created new table for '{delivery_id}' to {delta_path}")
    #print the number of new rows written
    print(f"new rows written: {dfw.count()}")
    #confirmation that the write succueded and prints our issues list
    return {"ok": True, "skipped": False, "issues": issues}


#delete delivery
def delete_delivery(delta_path: str,
                       ingest_dt: str,
                       delivery_id: str,
                       preview_only: bool = True):
    #get spark session and load delta table
    s = _get_spark()
    df = s.read.format("delta").load(delta_path)

    #checks if the table got the required columns
    cols = set(df.columns)
    if "ingest_dt" not in cols or "delivery_id" not in cols:
        raise ValueError("table must contain 'ingest_dt' and 'delivery_id' columns")
    #builds our condition that ingest_dt and delivery_id must be a match
    cond = (F.col("ingest_dt") == F.lit(ingest_dt)) & (F.col("delivery_id") == F.lit(delivery_id))
    #count how many rows matches the condition
    matches = df.filter(cond).count()
    #if it is in preview only mode or there is 0 matching rows it will not delete.
    if preview_only or matches == 0:
        #gives a small report
        return {"ok": True, "preview_only": True, "matches": matches}
    #load as delta table object and delete on condition
    dt = DeltaTable.forPath(s, delta_path)
    dt.delete(cond)
    
    #reading the file after deletion and gives a small report about deleted and remaing rows
    remaining = s.read.format("delta").load(delta_path).filter(cond).count()
    return {"ok": True, "preview_only": False, "deleted": matches - remaining, "remaining": remaining}
