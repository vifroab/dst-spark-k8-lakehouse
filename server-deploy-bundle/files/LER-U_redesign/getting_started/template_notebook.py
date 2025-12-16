# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: tags
#     notebook_metadata_filter: -widgets,-varInspector
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.18.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # DST-Spark Environment Verification
#
# This notebook actively demonstrates and verifies the platform's dynamic, branch-based environment switching.
#
# ## Key Feature
#
# The `spark_connector` module automatically configures the Spark session to connect to the correct resources (S3 buckets, Hive Metastore) based on the current Git branch. This notebook proves that the switching mechanism works as expected.
#
# ### Instructions
#
# Run the cells sequentially. Each "Verify" cell will:
# 1. Check out a specific Git branch.
# 2. Initialize a new Spark session for that branch's environment.
# 3. Print a summary of the environment's configuration.
# 4. Perform a live write/read test to confirm connectivity.

# %%
# Workaround for 'stopped SparkContext' error when re-running the notebook.
try:
    from pyspark.sql import SparkSession
    from pyspark.context import SparkContext

    if SparkContext._active_spark_context:
        SparkContext._active_spark_context.stop()

    SparkSession._instantiatedSession = None
    SparkSession._activeSession = None
except ImportError:
    pass
except Exception as e:
    print(f"Non-critical error during notebook reset: {e}")

from utilities.spark_connector import switch_spark_environment
import getpass
import subprocess

# %% [markdown]
# ## Step 1: Define the Verification Helper Function
#
# This function encapsulates the logic to switch branches, get a new Spark session, print the environment details, and run a live test.


# %%
def verify_environment_for_branch(branch_name):
    """
    Checks out a git branch, creates a Spark session, prints details,
    and performs a test operation.
    """
    spark = None  # Ensure spark is defined in the finally block's scope
    print("\n" + "=" * 80)
    print(f"🎬 Verifying Environment for Branch: '{branch_name}'")
    print("=" * 80)

    try:
        # --- 1. Switch Git Branch ---
        print(f"\n🔄 Switching to branch '{branch_name}'...")
        # Create branch if it doesn't exist, and ignore errors if it does.
        subprocess.run(
            ["git", "checkout", "-b", branch_name], capture_output=True, text=True
        )
        # Final checkout to ensure we are on it.
        result = subprocess.run(
            ["git", "checkout", branch_name], capture_output=True, text=True, check=True
        )
        print("✓ Git branch switched successfully.")

        # --- 2. Get New Spark Session ---
        print("\n⚡ Initializing new Spark session for this branch...")
        spark = switch_spark_environment()
        print("✓ Spark session created.")

        # --- 3. Print Environment Summary ---
        env_name = spark.conf.get("dst.env.name")
        bucket = spark.conf.get("dst.env.base_bucket")
        catalog = spark.conf.get("dst.env.catalog_type")
        hms_uri = spark.conf.get("spark.hadoop.hive.metastore.uris", "N/A (In-Memory)")

        print("\n" + "-" * 80)
        print("📋 Environment Configuration Summary:")
        print(f"   - Git Branch:    {branch_name}")
        print(f"   - Environment:   {env_name.upper()}")
        print(f"   - S3 Bucket:     {bucket}")
        print(f"   - Catalog Type:  {catalog}")
        print(f"   - Metastore URI: {hms_uri}")
        print("-" * 80)

        # --- 4. Perform Live Test ---
        print("\n🔬 Performing live write/read test...")
        username = spark.conf.get("dst.env.user")
        test_data = [(f"test_{env_name}", 1, username)]
        df_write = spark.createDataFrame(test_data, ["source", "id", "user"])

        # Use a safe, temporary table name
        temp_table = f"`leru_inte`.`verification_test_{username}`"

        # Define environments where developers should have restricted (read-only) access
        is_restricted_env = env_name in ["test", "prod"]

        if is_restricted_env:
            print(
                f"   - ({env_name.upper()} Environment): Verifying permissions are correctly RESTRICTED."
            )

            # Test 1: Verify WRITE operation FAILS as expected
            try:
                df_write.write.format("delta").mode("overwrite").saveAsTable(temp_table)
                # If this line is reached, it's a security failure.
                raise AssertionError(
                    f"Permissions Error: Write succeeded in '{env_name}', but should be restricted."
                )
            except Exception as e:
                # Check for a known S3 access denied error in the message
                if (
                    "Access Denied" in str(e)
                    or "Forbidden" in str(e)
                    or "DeltaIOException" in str(e)
                ):
                    print(
                        "   ✓ Write operation correctly FAILED with a permission error as expected."
                    )
                else:
                    print("   ✗ Write operation failed with an UNEXPECTED error.")
                    raise e  # Re-raise if it's not the error we want

            # Test 2: Verify READ operation SUCCEEDS
            print("   - Verifying read access...")
            spark.sql("SHOW DATABASES").collect()
            print("   ✓ Read operation (SHOW DATABASES) SUCCEEDED as expected.")

        else:  # For local-sandbox, sbx, and dev environments
            print(
                f"   - ({env_name.upper()} Environment): Verifying full read/write access."
            )

            # For the isolated sandbox, the test must create its own database
            is_isolated_sandbox = env_name == "local-sandbox"
            if is_isolated_sandbox:
                print(
                    "   - (Local Sandbox): Creating temporary database `leru_inte` for test..."
                )
                spark.sql("CREATE DATABASE IF NOT EXISTS `leru_inte`")

            df_write.write.format("delta").mode("overwrite").saveAsTable(temp_table)
            print(f"   ✓ Successfully wrote 1 row to {temp_table}")

            table_location = (
                spark.sql(f"DESCRIBE DETAIL {temp_table}")
                .select("location")
                .collect()[0][0]
            )
            print(f"   ✓ Table physically located at: {table_location}")

            if not table_location.startswith(bucket):
                raise AssertionError(
                    "Validation Error: Table location does not match the environment's bucket."
                )

            print("   ✓ Location matches expected bucket.")

        print("\n" + "=" * 80)
        print(f"✅ VERIFICATION SUCCEEDED for branch '{branch_name}'")
        print("=" * 80)

    except Exception as e:
        print("\n" + "!" * 80)
        print(f"❌ VERIFICATION FAILED for branch '{branch_name}'")
        print(f"   ERROR: {e}")
        print("!" * 80)
        import traceback

        traceback.print_exc()
        raise

    finally:
        # --- 5. Cleanup ---
        if spark:
            print("\n🧹 Cleaning up test table and stopping Spark session...")
            try:
                # Need to use the full username-specific table name
                username_cleanup = getpass.getuser().lower()
                table_to_drop = f"`leru_inte`.`verification_test_{username_cleanup}`"

                # Only try to drop the table if we are not in a restricted env,
                # since it would have failed to be created anyway.
                if "is_restricted_env" not in locals() or not is_restricted_env:
                    spark.sql(f"DROP TABLE IF EXISTS {table_to_drop}")
                    print("   ✓ Temporary table dropped.")

                # If it was an isolated sandbox, drop the entire temp database
                if "is_isolated_sandbox" in locals() and is_isolated_sandbox:
                    spark.sql("DROP DATABASE IF EXISTS `leru_inte` CASCADE")
                    print("   ✓ Temporary database `leru_inte` dropped.")

            except Exception as e:
                print(
                    f"   - Warning: Could not drop temp resources. They may not have been created. Error: {e}"
                )

            spark.stop()
            print("   ✓ Spark session stopped.")


# %% [markdown]
# ## Step 2: Run Verification for Each Environment
#
# The following cells will test the environment switching for each of the primary branch types.

# %%
# Verify the 'local-sandbox' environment
verify_environment_for_branch("local/my-temp-work")

# %%
# Verify the 'Shared Sandbox' (sbx) environment
verify_environment_for_branch("feature/new-collab-feature")

# %%
# Verify the 'dev' environment
verify_environment_for_branch("develop")

# %%
# Verify the 'test' environment
verify_environment_for_branch("release/v1.2.0")

# %%
# Verify the 'prod' environment
verify_environment_for_branch("main")

# %%
print("🎉 All environment verification checks are complete.")
