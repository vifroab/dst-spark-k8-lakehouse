# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: tags
#     formats: ipynb,py:percent
#     notebook_metadata_filter: -widgets,-varInspector
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.18.1
# ---

# %% [markdown]
"""
# SparkConnector Test Suite - Class-Based API

Covers:
- Class-based API and singleton pattern
- Branch-based environment switching
- HMS connectivity vs in-memory catalog
- Delta Lake write/read and time travel
- Resource configuration validation
- Context manager

Note: Tests create temp branches/databases/tables and clean up after themselves.
"""

# %%
import time
import subprocess
from pyspark.sql import Row
from utilities.spark_connector import SparkConnector

DEFAULT_TEST_SIZE = "XS"

# --- helpers -----------------------------------------------------------------


def _git_current_branch() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.DEVNULL
            )
            .strip()
            .decode("utf-8")
        )
    except Exception:
        return "unknown"


def _git_checkout(branch: str) -> None:
    subprocess.run(
        ["git", "checkout", "-b", branch],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(["git", "checkout", branch], capture_output=True, check=True)


def _drop_if_exists(spark, sql: str) -> None:
    try:
        spark.sql(sql)
    except Exception:
        pass


# --- core branch test ---------------------------------------------------------


def test_environment_for_branch(
    branch_name: str, expected_env: str, expected_catalog: str
) -> None:
    print("\n" + "=" * 80)
    print(f"🎬 Testing Environment: {branch_name} → {expected_env}")
    print("=" * 80)

    connector = None
    test_db = None
    is_restricted = True  # Assume restricted by default for safety in cleanup

    try:
        print(f"\n🔄 Switching to branch '{branch_name}'...")
        _git_checkout(branch_name)
        print("✓ Branch switched")

        connector = SparkConnector(size=DEFAULT_TEST_SIZE, force_new=True)
        spark = connector.session

        print("\n📋 Environment Validation:")
        print(f"  Branch:      {connector.env.branch}")
        print(f"  Environment: {connector.env.env_name}")
        print(f"  Catalog:     {connector.env.catalog_type}")
        print(f"  Bucket:      {connector.env.bucket}")
        print(f"  HMS URI:     {connector.env.hms_uri or '(in-memory)'}")

        assert connector.env.env_name == expected_env, f"Expected env '{expected_env}'"
        assert connector.env.catalog_type == expected_catalog, (
            f"Expected catalog '{expected_catalog}'"
        )

        print("\n🔍 Catalog checks...")
        if connector.env.catalog_type == "hive":
            hms_uri = spark.conf.get("spark.hadoop.hive.metastore.uris", "")
            assert hms_uri and "thrift://" in hms_uri, "HMS URI must be set for Hive"
            spark.sql("SHOW DATABASES").show()
            print("  ✓ HMS connectivity OK")
        else:
            assert not spark.conf.get("spark.hadoop.hive.metastore.uris", ""), (
                "HMS URI must be empty for in-memory"
            )
            spark.sql("SHOW DATABASES").show()
            print("  ✓ In-memory catalog OK")

        print("\n📝 Write/Read checks...")
        username = connector.env.username
        test_db = f"{username}_test"
        sanitized_env = expected_env.replace("-", "_")
        test_table = f"{test_db}.branch_test_{sanitized_env}"
        is_restricted = connector.env.env_name in ["test", "prod"]

        if is_restricted:
            print(
                f"  → {connector.env.env_name.upper()}: read-only expected, skipping write"
            )
            spark.sql("SHOW DATABASES").collect()
            print("  ✓ Read OK")
        else:
            # Create the database for any write-enabled environment
            print(f"  → Creating temporary database '{test_db}'...")
            spark.sql(f"CREATE DATABASE IF NOT EXISTS {test_db}")
            print("  ✓ Database created.")

            df = spark.createDataFrame(
                [(branch_name, expected_env, username)], ["branch", "env", "user"]
            )
            df.write.format("delta").mode("overwrite").saveAsTable(test_table)
            print(f"  ✓ Wrote to table '{test_table}'")
            spark.read.table(test_table).show()
            loc = (
                spark.sql(f"DESCRIBE DETAIL {test_table}")
                .select("location")
                .collect()[0][0]
            )
            assert connector.env.bucket.replace("s3a://", "") in loc, (
                "Table not in expected bucket"
            )
            print(f"  ✓ Location verified: {loc}")

        print("\n" + "=" * 80)
        print(f"✅ ENVIRONMENT TEST PASSED: {branch_name} → {expected_env}")
        print("=" * 80)

    finally:
        if connector and connector.is_active:
            # If the environment was write-enabled, we created a database and must clean it up.
            if not is_restricted and test_db:
                print(f"🧹 Cleaning up test database '{test_db}'...")
                _drop_if_exists(spark, f"DROP DATABASE IF EXISTS {test_db} CASCADE")
                print("  ✓ Cleanup complete.")
            connector.stop()


# --- main sequence ------------------------------------------------------------

if __name__ == "__main__":
    original_branch = _git_current_branch()
    connector = None

    try:
        # 1) Resource sizes (Simplified to just acknowledge the test size)
        print("\n" + "=" * 80)
        print(f"📊 TEST 1: Running all tests with default size: {DEFAULT_TEST_SIZE}")
        print("=" * 80)

        # 2) Basic class API
        print("\n" + "=" * 80)
        print("🧪 TEST 2: Class-Based API")
        print("=" * 80)
        connector = SparkConnector(size=DEFAULT_TEST_SIZE)
        spark = connector.session
        print(f"Spark {spark.version}, app={spark.sparkContext.appName}")
        spark.sql("SELECT 'Class-based API works! 🎉' as message").show()
        print(
            "  env:",
            connector.env.env_name,
            connector.env.catalog_type,
            connector.env.bucket,
        )

        # 3) Singleton
        print("\n" + "=" * 80)
        print("🧪 TEST 3: Singleton")
        print("=" * 80)
        c2 = SparkConnector(size=DEFAULT_TEST_SIZE)
        print("same instance:", connector is c2)
        print("same session:", connector.session is c2.session)

        # 4) Env via spark.conf
        print("\n" + "=" * 80)
        print("🧪 TEST 4: Env via spark.conf")
        print("=" * 80)
        assert spark.env.env_name == spark.conf.get("dst.env.env_name")
        assert spark.env.bucket == spark.conf.get("dst.env.bucket")
        print("  ✓ spark.env and spark.conf match")

        # 5) Delta I/O basic
        print("\n" + "=" * 80)
        print("🧪 TEST 5: Delta read/write")
        print("=" * 80)
        data = [
            Row(id=1, name="Alice", salary=120000),
            Row(id=2, name="Bob", salary=95000),
            Row(id=3, name="Charlie", salary=110000),
        ]
        df = spark.createDataFrame(data)
        path = f"{connector.env.bucket}/test/class_api_basic"
        df.write.format("delta").mode("overwrite").save(path)
        spark.read.format("delta").load(path).show()
        print("  ✓ Delta I/O OK")

        # 6) Context manager
        print("\n" + "=" * 80)
        print("🧪 TEST 6: Context manager")
        print("=" * 80)
        with SparkConnector(size=DEFAULT_TEST_SIZE) as sp:
            sp.sql("SELECT 'Context manager OK' as msg").show()

        connector.stop()
        connector = None

        # 7-11) Branch-based environments
        test_environment_for_branch("local/test-sandbox", "local-sandbox", "in-memory")
        test_environment_for_branch("feature/test-sbx", "sbx", "hive")
        test_environment_for_branch("develop", "dev", "hive")
        test_environment_for_branch("release/v1.0.0", "test", "hive")
        test_environment_for_branch("main", "prod", "hive")

        # 12) Delta versioning/time travel (on dev)
        print("\n" + "=" * 80)
        print("🧪 TEST 12: Delta Versioning & Time Travel")
        print("=" * 80)
        _git_checkout("develop")
        connector = SparkConnector(size=DEFAULT_TEST_SIZE, force_new=True)
        spark = connector.session

        username = connector.env.username
        test_db = f"{username}_test"
        test_table = f"{test_db}.version_test"

        spark.sql(f"CREATE DATABASE IF NOT EXISTS {test_db}")

        v0 = [(1, "Product A", 100), (2, "Product B", 200), (3, "Product C", 150)]
        spark.createDataFrame(v0, ["id", "product", "price"]).write.format(
            "delta"
        ).mode("overwrite").saveAsTable(test_table)
        time.sleep(2)
        v1 = [(1, "Product A", 120), (2, "Product B", 180), (4, "Product D", 250)]
        spark.createDataFrame(v1, ["id", "product", "price"]).write.format(
            "delta"
        ).mode("overwrite").saveAsTable(test_table)

        latest = spark.read.table(test_table).orderBy("id").collect()
        print("LATEST:", [dict(r.asDict()) for r in latest])

        v0_read = (
            spark.read.format("delta")
            .option("versionAsOf", 0)
            .table(test_table)
            .orderBy("id")
            .collect()
        )
        print("V0:", [dict(r.asDict()) for r in v0_read])

        assert len(latest) == 3 and len(v0_read) == 3
        assert [r for r in latest if r["product"] == "Product A"][0]["price"] == 120
        assert [r for r in v0_read if r["product"] == "Product A"][0]["price"] == 100
        print("  ✓ Time travel OK")

        _drop_if_exists(spark, f"DROP TABLE IF EXISTS {test_table}")
        _drop_if_exists(spark, f"DROP DATABASE IF EXISTS {test_db} CASCADE")
        connector.stop()
        connector = None

        # 13) Resource configuration validation
        print("\n" + "=" * 80)
        print("🧪 TEST 13: Resource configuration validation")
        print("=" * 80)

        print(f"  → Verifying size: {DEFAULT_TEST_SIZE}")
        connector = SparkConnector(size=DEFAULT_TEST_SIZE, force_new=True)

        conf = connector.session.sparkContext.getConf()
        res = connector.env.resource

        # Manually check against the expected XS values
        assert res.size == "XS"
        assert conf.get("spark.cores.max") == "2"
        assert conf.get("spark.executor.cores") == "1"
        assert conf.get("spark.executor.memory") == "2g"

        print(f"  ✓ {DEFAULT_TEST_SIZE} configuration applied correctly")
        connector.stop()
        connector = None

        # 14) Branch mismatch detection
        print("\n" + "=" * 80)
        print("🧪 TEST 14: Branch mismatch warning")
        print("=" * 80)
        _git_checkout("develop")
        c1 = SparkConnector(size=DEFAULT_TEST_SIZE, force_new=True)
        print("   Session branch:", c1.env.branch)
        _git_checkout("feature/branch-mismatch")
        c2 = SparkConnector(size=DEFAULT_TEST_SIZE)  # should warn
        c2.restart()
        print("   After restart branch:", c2.env.branch)
        c2.stop()

        print("\n" + "=" * 80)
        print("🎉 ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 80)

    finally:
        # Cleanup and return to original branch
        if connector and connector.is_active:
            connector.stop()
        if original_branch and original_branch != "unknown":
            try:
                subprocess.run(
                    ["git", "checkout", original_branch], capture_output=True
                )
            except Exception:
                pass

# %%
connector._session

# %%
