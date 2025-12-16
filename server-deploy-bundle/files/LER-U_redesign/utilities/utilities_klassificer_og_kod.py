# Funktioner til 5.2 - Klassificer og kod data
from pyspark.sql import functions as F

def norm(c):
    """
    Trimmer kolonnen og konverterer tomme strenge til NULL.
    """
    col = F.col(c) if isinstance(c, str) else c
    return F.nullif(F.trim(col), F.lit(""))

def filter_stil_data(df, cols):
    """
    Filtrerer STIL-data til HOMR=2 eller 3 og udvælger relevante kolonner.
    Printer, hvis nogle kolonner mangler
    """
    
    df = df.filter(F.col("HOMR").isin("2", "3"))

    df = df.select(cols)

    # Vælg kun de kolonner, der findes i df; rapportér de manglende
    present = [c for c in cols if c in df.columns]
    missing = [c for c in cols if c not in df.columns]

    df = df.select([F.col(c) for c in present])

    if missing:
        print("Mangler kolonner:", missing)

    return df

def trim_string_columns(df, cols):
    """
    Fjerner foranstillede og efterstillede mellemrum i udvalgte tekstkolonner i et PySpark DataFrame.

    Parametre
    ----------
    df : pyspark.sql.DataFrame
        Det input-DataFrame, hvor kolonnerne skal trimmes.
    cols_to_trim : list af str
        Liste over kolonnenavne, som ønskes trimmet.

    Returnerer
    ----------
    pyspark.sql.DataFrame
        Et nyt DataFrame, hvor de angivne tekstkolonner er trimmet.

    Bemærk
    -------
    - Kun kolonner med datatype 'string' bliver trimmet.
    - Hvis nogle af de angivne kolonner ikke findes eller ikke er af typen 'string',
      bliver de sprunget over, og der udskrives en besked med disse kolonnenavne.
    """
    # Find kolonner der er af typen string
    string_cols = {c for c, t in df.dtypes if t == "string"}

    # Find de ønskede kolonner, som faktisk er strings
    targets = [c for c in cols if c in string_cols]

    # Trim de udvalgte kolonner
    for c in targets:
        df = df.withColumn(c, F.trim(F.col(c)))

    # Tjek om nogle kolonner blev sprunget over
    skipped = [c for c in cols if c not in string_cols]
    if skipped:
        print("Sprunget over – manglende eller ikke-string kolonner:", skipped)

    return df


def count_empty_values(df, column):
    """
    Tæller hvor mange rækker i en kolonne er tomme ('' or null)
    og printer resultatet med den totalle count og procent.
    """
    total_count = df.count()
    
    # Definér "empty" som enten NULL eller tom string
    empty_count = df.filter((F.col(column).isNull()) | (F.col(column) == "")).count()
    
    # Print formateret output
    print(
        f"Empty values in '{column}': {empty_count:,} out of {total_count:,} "
        f"rows ({empty_count / total_count:.2%})")

def extract_speciale(df, source_col="speciale", target_col="specs"):
    """
    Funktionen udleder SPEC, som "specs" udfra variablen "speciale".
    """

    # Definer møsnter
    pattern = r"speciale=([^)]*)"

    return df.withColumn(
        target_col,
        F.regexp_extract(F.col(source_col), pattern, 1)
    )

def extract_spec(df):
    df = df.withColumn(
    "specs",
    F.regexp_extract(F.col("speciale"), r"\((\d{2})", 1)
    )

    return df

def add_UDEL(df):
    """
    Tager en dataframe (STIL data for EUD og GYM), og tilføjer en ny kollone for UDEL
    ---------
    UDEL defineres som substring (de sidste 2 cifre) af "UDD6"
    ---------
    Output: En dataframe med UDEL-kolonne tilføjet
    """
    return df.withColumn("UDEL", F.substring(F.col("UDD6"), -2, 2))


def add_UFORM(df):
    """
    Tager en dataframe (STIL data for EUD og GYM), og tilføjer en ny kollone for UFORM
    ---------
    UDEL defineres udfra kombinationen af "tilrettelaeggelse" og "skoleEllerPraktikvej_EUD"
    ---------
    Output: En dataframe med UFORM-kolonne tilføjet
    """

    # Variablene ensrettes til UPPERCASE
    tilret_up = F.upper(F.coalesce(F.col("tilrettelaeggelse"), F.lit("")))
    skolepr_up = F.upper(F.coalesce(F.col("skoleEllerPraktikvej_EUD"), F.lit("")))

    # Betingelser defineres
    cond1 = tilret_up.contains("MESTER")
    cond2 = tilret_up.contains("EUX") & (skolepr_up == "OPLÆRINGSVEJ")
    cond3 = tilret_up.contains("EUX") & (skolepr_up == "SKOLEVEJ")
    cond4 = F.col("tilrettelaeggelse").contains("GYM")
    cond5 = (~tilret_up.contains("EUX")) & (skolepr_up == "OPLÆRINGSVEJ")
    cond6 = (~tilret_up.contains("EUX")) & (skolepr_up == "SKOLEVEJ")

    # UFORM-værdien tildeles for hver betingelse
    df = df.withColumn(
            "UFORM",
            F.when(cond1, "40")
             .when(cond2, "47")
             .when(cond3, "48")
             .when(cond4, "45")
             .when(cond5, "41")
             .when(cond6, "42")
             .otherwise("00")
        )

    return df

def add_AUDD(df):
    """
    Dataframe tages som input, og kolonne "AUDD" tilføjes
    ---------
    AUDD defineres som:
    - Hvis uddannelsesforløb i gang, AUDD = 9999
    - Hvis udannelsesforløb fuldført, AUDD = UDD
    - Hvis udannelsesforløb afbrudt, AUDD = 0000

    Dette er den første tildeling af AUDD koder, herefter skal data igennem funktioner, som følger regler for henholdsvis
    EUD og GYM.
    ---------
    Output: En dataframe med AUDD-kolonne tilføjet
    """
    df = df.withColumn(
        "AUDD",
        F.when(F.col("afgart_UDD6") == "1", F.lit("9999"))            # i gang
         .when(F.col("afgart_UDD6") == "2", F.col("UDD").cast("string"))  # fuldført
         .when(F.col("afgart_UDD6") == "3", F.lit("0000"))            # afbrudt
         .otherwise(F.lit("FEJL"))
    )
    # Hvis vedkomne er i gang ændres slut datoen til 9999-12-31
    df = df.withColumn(
        "afgtp",
        F.when(F.col("afgart_UDD6") == "1", F.lit("9999-12-31"))
         .otherwise(F.col("afgtp"))
    )
    return df

def add_AUDD_gym(df):
    """
    Dataframe tages som input, og kolonne "AUDD" tilføjes
    ---------
    AUDD defineres for fuldførte gymnasiseforløb (afgart_UDD6 = 2 og HOMR = 2)
    Her bruges direkte tildeling af AUDD-koder ud fra UDD og UDEL
    ---------
    Output: En dataframe med AUDD-kolonne tilføjet
    """
    cond1 = (F.col("afgart_UDD6") == "2") & (F.col("HOMR") == "2") & (F.col("UDD") == "1199")
    cond2 = (F.col("afgart_UDD6") == "2") & (F.col("HOMR") == "2") & (F.col("UDD") == "1539")
    cond3 = (F.col("afgart_UDD6") == "2") & (F.col("HOMR") == "2") & (F.col("UDD") == "5090")
    cond4 = (F.col("afgart_UDD6") == "2") & (F.col("HOMR") == "2") & (F.col("UDD") == "5080")
    cond5 = (F.col("afgart_UDD6") == "2") & (F.col("HOMR") == "2") & (F.col("UDD") == "1652")
    cond6 = (F.col("afgart_UDD6") == "2") & (F.col("HOMR") == "2") & (F.col("UDD") == "1899")    

    df = df.withColumn(
        "AUDD",
        F.when(cond1,
               F.when(F.col("UDEL") == "21", "1196")
                .when(F.col("UDEL") == "22", "1197")
                .when(F.col("UDEL") == "23", "1198")
                .otherwise(F.col("AUDD"))
             )
        .when(cond2,
               F.when(F.col("UDEL") == "21", "1531")
                .when(F.col("UDEL").isin(["22", "23", "24"]), "1532")
                .otherwise(F.col("AUDD"))
             )
        .when(cond3,
               F.when(F.col("UDEL") == "21", "5028")
                .when(F.col("UDEL") == "22", "5029")
                .when(F.col("UDEL") == "23", "5098")
                .otherwise(F.col("AUDD"))
             )
        .when(cond4,
               F.when(F.col("UDEL") == "21", "5081")
                .when(F.col("UDEL") == "22", "5029")
                .when(F.col("UDEL") == "23", "5098")
                .otherwise(F.col("AUDD"))
             )
        .when(cond5,
               F.when(F.col("UDEL") == "21", "1650")
                .when(F.col("UDEL") == "22", "1651")
                .otherwise(F.col("AUDD"))
             )
        .when(cond6,
               F.when(F.col("UDEL") == "21", "1892")
                .when(F.col("UDEL") == "22", "1893")
                .otherwise(F.col("AUDD"))
             )
        .otherwise(F.col("AUDD"))
    )

    return df

def add_AUDD_eud(df, df_konv):
    """
    Tager 2 DataFrames som input (gym_eud og cøsa-konvertering) og udfylder AUDD for EUD.
    ------------------------------------------------------------
    AUDD defineres udfra direkte regler og brug af CØSA-konvertering (på UDD, SPEC og CØSA)
    ------------------------------------------------------------
    Output: En DataFrame med opdateret AUDD-kolonne.
    """

    # 1) Direkte regler
    condition = (F.col("HOMR") == "3") & (F.col("afgart_UDD6") == "2")

    df = df.withColumn(
        "AUDD",
        F.when(condition & F.col("UDEL").isin("53", "54"), "3598")
         .when(condition & (F.col("UDEL") == "55"), "3597")
         .otherwise(F.col("AUDD"))
    )

    # 2) Opslag på UDD+SPEC+COSA
    konv_alias = df_konv.select(
        norm("UDD").alias("konv_UDD_norm"),
        norm("SPEC").alias("konv_SPEC_norm"),
        norm("COSA").alias("konv_COSA_norm"),
        F.col("AUDD").alias("konv_AUDD"),
    )

    join_condition = (
        norm("UDD").eqNullSafe(F.col("konv_UDD_norm")) &
        norm("specs").eqNullSafe(F.col("konv_SPEC_norm")) &
        norm("coesa").eqNullSafe(F.col("konv_COSA_norm"))
    )

    df_joined = df.join(konv_alias, on=join_condition, how="left")

    # 3) Udfyld AUDD for UDEL i {"00","51","56","52"} når opslag findes
    df_result = (df_joined
        .withColumn(
            "AUDD",
            F.when(
                condition
                & F.col("UDEL").isin("00", "51", "56", "52")
                & F.col("konv_AUDD").isNotNull(),
                F.col("konv_AUDD")
            ).otherwise(F.col("AUDD"))
        )
        .drop("konv_UDD_norm", "konv_SPEC_norm", "konv_COSA_norm", "konv_AUDD") # dropper kolonner fra konverteringen
    )
    
    return df_result

def add_hinstnr(df, df_instreg):
    """
    Joiner STIL-data med instreg for at tilføje kolonnen 'hinstnr'.
    Hvis HOSKINST = 999999, anvendes inst som erstatning.
    """
    
    df = df.alias("df")
    df2 = df_instreg.alias("df2")

    # Nøgler: gør tom/whitespace til NULL og cast til string
    left_key  = F.when(F.length(F.trim(F.col("df.inst"))) == 0, None) \
                 .otherwise(F.col("df.inst")).cast("string")
    right_key = F.col("df2.INSTNR").cast("string")

    df = (
        df.join(df2, left_key.eqNullSafe(right_key), "left")
          .withColumn(
              "hinstnr",
              F.when(F.col("df2.HOSKINST").cast("string") == F.lit("999999"),
                     F.col("df.inst").cast("string"))
               .otherwise(F.col("df2.HOSKINST").cast("string"))
          )
          # drop kun højre DF’s kolonner
          .drop(F.col("df2.INSTNR"), F.col("df2.HOSKINST"))
    )
    # returner STIL data 
    return df
