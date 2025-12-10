import os

def count_files(path, fs=None):
    # fs can be NFS, S3, DBFS, etc.  
    # For now assume local/NFS:
    if not os.path.exists(path):
        return 0
    return len([f for f in os.listdir(path) if not f.startswith(".")])

def df_count(df):
    return df.count()

def df_avg(df, column):
    row = df.agg({column: "avg"}).collect()
    if row and row[0][0] is not None:
        return row[0][0]
    return 0.0

def df_error_count(df, error_column="is_error"):
    if error_column in df.columns:
        return df.filter(df[error_column] == True).count()
    return 0

