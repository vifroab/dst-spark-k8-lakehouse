#inititate spark
from utilities.spark_connector import SparkConnector

connector = SparkConnector(size="L")
spark = connector.session

#----------Remove duplicates----------


#Get todays date and define table name
DATO = date.today()
TABLE_NAME = f"elev_stil6_{DATO}"

#The input path of the table we are going to work with
INPUT_PATH = f"{connector.env.bucket}/stil6/02_skemaindlaest/{TABLE_NAME}"


#The target deliveries that we want to deduplicate
TARGET_LEVERANCER = ["current", "old_delivery_1", "old_delivery_2", "broken_delivery"]

#-----------Integration-------------

#Output path to where the integrated data is saved
DELTA_PATH = f"{connector.env.bucket}/stil6/03_integreret/{TABLE_NAME}"

#CURRENT_DELIVERY should use the delivery_id of the current data (What we are going to replace)
CURR_DELIVERY = "current"

#NEW_DELIVERY should use the delivery id of the new delivery (What we are going to replace with)
NEW_DELIVERY  = "old_delivery_1"