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
# DST-Spark Connector Demonstration

This notebook demonstrates the key features of the `SparkConnector` class, including:
- Automatic connection and environment detection.
- Default use of **Dynamic Allocation** for efficient resource sharing.
- Default use of **Delta Lake** for all data writes.
- Safe handling of **Git Branch Switches**.
"""

# %% [markdown]
"""
### 1. Initial Setup

First, we import the necessary tools and set our git branch to a clean state for the demonstration. We will start with a `local/` branch, which connects to an isolated, in-memory sandbox.
"""

# %%
import subprocess
import time
from pyspark.sql import Row
from utilities.spark_connector import SparkConnector

# Ensure we start on a predictable branch
try:
    subprocess.run(
        ["git", "checkout", "-b", "local/connector-demo"], stderr=subprocess.DEVNULL
    )
except:
    subprocess.run(["git", "checkout", "local/connector-demo"])

print("Git branch is set to 'local/connector-demo'")

# %% [markdown]
"""
### 2. Creating a Spark Connection

To get a Spark session, simply create an instance of `SparkConnector`.

By default, the connector enables **Dynamic Allocation**. This means Spark will automatically release executors (the "runners") after a period of inactivity, making them available for other users. The default idle timeout is 10 minutes.

Let's create a session with a shorter timeout to demonstrate this feature.
"""

# %%
# Create the connector. Dynamic allocation is on by default.
# We'll set a short idle timeout for demonstration purposes.
connector = SparkConnector(size="XS", idle_timeout="60s")

# The SparkSession is accessed via the .session property
spark = connector.session

# The connector provides detailed environment info via the .env property
print("\n--- Environment Details ---")
print(f"Environment Name: {connector.env.env_name}")
print(f"Catalog Type:     {connector.env.catalog_type}")
print(f"Target S3 Bucket: {connector.env.bucket}")
print(f"Resource Size:    {connector.env.resource.size}")

# You can verify that dynamic allocation is enabled in the Spark config
is_dynamic = spark.conf.get("spark.dynamicAllocation.enabled")
timeout = spark.conf.get("spark.dynamicAllocation.executorIdleTimeout")
print(f"\nDynamic Allocation Enabled: {is_dynamic}")
print(f"Executor Idle Timeout:      {timeout}")


# %% [markdown]
"""
### 3. Demonstrating Dynamic Allocation and Resource Release

Now, let's run a small job. This will cause Spark to acquire executors. After the job is done, if we wait for the `executorIdleTimeout` (60 seconds in our case), Spark will automatically release them.

**To see this in action:**
1. Run the cell below.
2. Quickly open the **Spark Master UI** in your browser (usually at `http://localhost:8080`).
3. You will see your application running with active executors.
4. Wait for about 60 seconds **without running any other Spark commands**.
5. Refresh the Spark UI. You will see the executors have been removed, and their resources are now free.
"""

# %%
print("Running a sample Spark job to acquire executors...")
spark.range(1000).toDF("id").write.mode("overwrite").save(
    f"{connector.env.bucket}/demo/dynamic_alloc_test"
)
print("✅ Job complete. Executors are now idle.")
print(
    "\nCheck the Spark UI at http://localhost:8080. After 60 seconds, the executors for this app will be released."
)
print("Waiting for 70 seconds to simulate inactivity...")

# We'll wait here to let the timeout expire
time.sleep(70)

print("\n70 seconds have passed.")
print("If you refresh the Spark UI, the executors should now be gone.")
print("\nRunning a new job will re-acquire them automatically...")
count = spark.range(500).count()
print(f"✅ New job ran successfully. Counted {count} rows.")
print("Check the Spark UI again; the executors have returned.")


# %% [markdown]
"""
### 4. Writing Data with Delta as the Default Format

The connector is configured to use **Delta Lake as the default storage format**. This means you don't need to specify `.format("delta")` for your write operations.

Let's save a DataFrame without specifying the format to confirm it creates a Delta table.
"""

# %%
# Create some sample data
data = [Row(id=1, status="new"), Row(id=2, status="pending")]
df = spark.createDataFrame(data)

# Define a path in our user-specific sandbox bucket
write_path = f"{connector.env.bucket}/demo/default_delta_table"

# Write the data. Notice we DO NOT specify .format("delta").
print(f"Writing DataFrame to: {write_path}")
df.write.mode("overwrite").save(write_path)
print("✅ Write successful!")

# Verify that it was written as a Delta table by reading it back
print("\nReading the data back...")
df_read = spark.read.load(write_path)
df_read.show()


# %% [markdown]
"""
### 5. Handling a Git Branch Switch

When you switch git branches, the active Spark session becomes invalid for the new environment. The connector detects this and warns you. The correct way to sync your session is to call `connector.restart()`.

Let's switch to a `feature/` branch. This will connect us to the shared `sbx` (Sandbox) environment, which uses a persistent Hive Metastore.
"""

# %%
# First, let's switch the git branch
new_branch = "feature/new-demo-feature"
try:
    subprocess.run(["git", "checkout", "-b", new_branch], stderr=subprocess.DEVNULL)
except:
    subprocess.run(["git", "checkout", new_branch])
print(f"Git branch switched to: '{new_branch}'")

# Now, if we try to get a session again, the connector will issue a warning
print("\n--- Attempting to use the old connector after branch switch ---")
connector_after_switch = SparkConnector()

# %% [markdown]
"""
As shown by the warning, the connector has detected the mismatch. Let's use `restart()` to get a new session that is correctly configured for our new branch.

**Important:** After a restart, you should re-assign your `spark` variable to point to the new session.
"""

# %%
print("\n--- Restarting the connector to align with the new branch ---")
# The restart method returns the re-initialized connector instance.
connector = connector.restart(size="XS")

# Re-assign the spark variable to point to the new, active session
spark = connector.session

print("\n--- New Environment Details ---")
print(f"Environment Name: {connector.env.env_name}")
print(f"Catalog Type:     {connector.env.catalog_type}")
print(f"Target S3 Bucket: {connector.env.bucket}")
print(f"HMS URI:          {connector.env.hms_uri}")

# Since we are now connected to Hive, we can see the available databases
print("\n--- Databases in Hive Metastore ---")
spark.sql("SHOW DATABASES").show()
spark.sql("SHOW TABLES IN default;").show()


# %% [markdown]
"""
### 6. Automatic Environment Bootstrapping

The connector can synchronize your S3 data lake with the Hive Metastore, making your data queryable via SQL. The `bootstrap()` method is designed to be fully automatic.

- **In a personal sandbox (`local/` branch):** It defaults to using your username as the domain, setting up your personal workspace.
- **In a shared environment (`feature/` branch):** It auto-detects the project domain from the bucket structure.

Let's see this in action.
"""

# %%
# First, let's bootstrap the shared domain we are currently connected to.
# The connector will scan the 'sbx' bucket and find our project domain automatically.
print("\n--- Bootstrapping in a shared (sbx) environment ---")
connector.bootstrap()

# We can now see the databases that were created for our auto-detected domain
print("\n--- Databases after bootstrapping shared domain ---")
spark.sql("SHOW DATABASES").show()

# %% [markdown]
"""
Now, let's switch back to our personal sandbox and see how bootstrapping works there.
"""

# %%
# Switch back to the local branch and restart the connector
print("\n--- Switching back to local sandbox environment ---")
subprocess.run(["git", "checkout", "local/connector-demo"])
connector = connector.restart(size="XS", idle_timeout="60s")
spark = connector.session  # Re-assign spark variable again

# Now, run bootstrap with no arguments
print("\n--- Bootstrapping in a personal (local-sandbox) environment ---")
connector.bootstrap()

# The connector should have automatically used your username as the domain
print("\n--- Databases after bootstrapping personal domain ---")
spark.sql("SHOW DATABASES").show()


# %% [markdown]
"""
### 7. Cleaning Up

When you are finished, stop the Spark session to free up all resources associated with the driver.
"""

# %%
print("Demonstration complete. Stopping the Spark session.")
connector.stop()

# You can verify that the session is no longer active
print(f"\nIs the connector active? {connector.is_active}")

# Return to the original branch for a clean state
subprocess.run(["git", "checkout", "local/connector-demo"])
print("\nReturned to original branch.")

# %%
connector._print_config()

# %%

# %%
