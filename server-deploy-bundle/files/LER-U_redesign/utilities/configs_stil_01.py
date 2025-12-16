#----------Configuration for appending delivery----------

#The path where the treated data will be stored
TABLE_NAME    = "/kdrev/stil_data/config_test"

#The path where the new delivery will be loaded from
INPUT_PATH    = "s3a://dev/k_drev/stil_leverencer/stil_niv6_gammel_4_c.csv"

#Metadata to explain where the data is from
SOURCE_SYSTEM = "STIL"

# The delivery id will be put on the delivery so it always can be identified. You can speicifiy it yourself (in string format) or if it is set to None it will autogenerate an id based on the file name and the current time.
DELIVERY_ID   = "broken_delivery"

#This is columns that will be required from the delivery. If these are not included it will tell you in the report
REQUIRED_COLS = [
    "pnr", "inst", "tilrettelaeggelse", "speciale", "afgart_UDD6",
    "speciale", "tilgtp", "afgtp", "skoleEllerPraktikvej_EUD",
    "coesa", "HOMR", "foerste_UDD6", "afgart_HOMR", "HGRP", "afgart_HGRP"
]

#Automatically rename a column
RENAMES = {"cpr": "pnr"}

#If set to True it will allow to append the delivery even though the source_fingerprint or delivery_id exists
FORCE_RELOAD = False

#If set to true it will allow to append the delivery even though there is a column mismatch (extra or missing columns)
FORCE_SCHEMA = False

#If set to true it will never append or write (you can use this if you just want to see the report)
DRY_RUN = False


#----------Configuration for deleting delivery----------

#The path to the table where a delivery will be deleted
TABLE_NAME_DELETE    = "/kdrev/stil_data/config_test"

#The delivery ID of the delivery you want to delete
DELIVERY_ID_TO_DELETE = "broken_delivery"

#The ingestion date for the delivery you want to delete
INGEST_DT_TO_DELETE = "2025-11-25"

#If set to True it will not delete only preview
PREVIEW_ONLY = True