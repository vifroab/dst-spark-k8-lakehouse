# Funktioner til 5.3 - Gennemgå og fejlssøg
from pyspark.sql import functions as F
from datetime import date, datetime, timedelta

def count_errors(df_error, df_total):
    """
    Tæller antal fejl (rækker i df_error) i forhold til det samlede antal observationer (df_total).

    Parameters
    ----------
    df_error : DataFrame
        DataFrame med de rækker, der indeholder fejl.
    df_total : DataFrame
        Det samlede datasæt.
    label : str, optional
        En beskrivende tekst til udskriften (standard = "Fejl").
    """
    total_count = df_total.count()
    error_count = df_error.count()

    print(
        f"{df_error}: {error_count:,} ud af {total_count:,} rækker "
        f"({error_count / total_count:.2%})"
    )

def show_nulls_in_column(df, column, include_empty: bool = False, show_n: int = 20):
    """
    Viser alle rækker, hvor en bestemt kolonne er NULL (eller evt. tom),
    og udskriver antal samt andel af de manglende værdier.

    Parametre
    ----------
    df : pyspark.sql.DataFrame
        DataFrame, der skal undersøges.
    kolonne : str
        Navnet på kolonnen, der skal tjekkes.
    inkluder_tomme : bool, optional
        Hvis True, tælles tomme strenge ("") også som manglende værdier. Standard = False.
    vis_n : int, optional
        Antal rækker der vises (standard = 20).
    """

    total_count = df.count()
    cond = F.col(column).isNull()
    if include_empty:
        cond = cond | (F.col(column) == "")

    df_nulls = df.filter(cond)
    null_count = df_nulls.count()

    if total_count == 0:
        print("Error")
        return

    # Print stats
    print(
        f"Missing values in '{column}': {null_count:,} out of {total_count:,} rows "
        f"({null_count / total_count:.2%})"
    )

def flag_invalid_intervals(df, start_col="tilgtp", end_col="afgtp"):
    """
    Tilføjer en boolean kolonne 'invalid_interval', som indikere om tilgtp > afgtp.
    """
    return df.withColumn(
        "invalid_interval",
        F.when(F.col(start_col) >= F.col(end_col), F.lit(True)).otherwise(F.lit(False))
    )
    
def missing_ids(df1, df2, id_col_left="UDD", id_col_right=None):
    """
    Returns a DataFrame with all rows from df1 where the id_col_left
    value is NOT found in df2's id_col_right (or the same column if None).
    """
    # Default to same name if not provided
    id_col_right = id_col_right or id_col_left

    # Select distinct IDs from df2 for faster join
    df2_ids = df2.select(F.col(id_col_right).alias(id_col_left)).distinct()

    # Left anti join keeps rows from df1 with no match in df2
    missing = df1.join(df2_ids, on=id_col_left, how="left_anti")

    return missing

def missing_audd(df1, df2, id_col_left="AUDD", id_col_right=None):
    """
    Returns a DataFrame with all rows from df1 where the id_col_left
    value is NOT found in df2's id_col_right (or the same column if None).
    """
    # Default to same name if not provided
    df1 = df1.filter((F.col("afgart_UDD6") == "2") & (F.col("HOMR") == "3"))

    # Default to same name if not provided
    id_col_right = id_col_right or id_col_left

    # Select distinct IDs from df2 for faster join
    df2_ids = df2.select(F.col(id_col_right).alias(id_col_left)).distinct()

    # Left anti join keeps rows from df1 with no match in df2
    missing = df1.join(df2_ids, on=id_col_left, how="left_anti")

    return missing

def find_duplicate_combinations(df, cols, null_equal=False):
    """
    Return all rows from df where the combination in `cols` occurs > 1 time.

    - cols: list/tuple of column names (e.g., ["A","B","C","D"])
    - null_equal=False: normal SQL semantics (NULLs don't match in the join)
      If True, treat NULLs as equal by normalizing them to a sentinel.
    """
    if not cols:
        raise ValueError("`cols` must be a non-empty list of column names.")

    if null_equal:
        # Normalize NULLs so they compare as equal in the join
        key_cols = [F.coalesce(F.col(c).cast("string"), F.lit("__NULL__")).alias(f"__k_{c}") for c in cols]
        keyed = df.select(*df.columns, *key_cols)
        knames = [f"__k_{c}" for c in cols]

        dup_keys = (
            keyed.groupBy(*knames)
                 .count()
                 .filter(F.col("count") > 1)
                 .select(*knames)
        )
        out = keyed.join(dup_keys, on=knames, how="inner").drop(*knames)
    else:
        dup_keys = (
            df.groupBy(*cols)
              .count()
              .filter(F.col("count") > 1)
              .select(*cols)
        )
        out = df.join(dup_keys, on=cols, how="inner")

    return out

def wrong_end_date(df):
    """
    Returnér alle rækker fra `df`, hvor 'afgtp' ligger efter eller på den sidste dag i det indeværende år,
    og hvor 'afgart_UDD6' er lig med "2" (Undervisningsforløb fuldført).

    - df: Spark DataFrame
    - Datoafgrænsningen beregnes dynamisk ud fra leverancedato, og cutoff defineres som sidste dag i måneden inden leverancedatoen
    - Bruges til at finde observationer med ugyldige eller fremtidige slutdatoer.
    """
    # Definer leverancedato, som d.d.
    # SKAL RETTES til en korrekt leverancedato
    leverancedato = date.today()

    # Find sidste dag i måenden før leverancedato
    cutoff_date = leverancedato.replace(day=1) - timedelta(days=1)

    df = df.filter((F.col("afgtp") >= F.lit(cutoff_date)) & (F.col("afgart_UDD6") == "2"))
    
    return df

def missing_udd_udel_uform_kombi(df1, df2, col1="UDD", col2="UDEL", col3="UFORM"):
    """
    Returnerer alle rækker from df1, hvor UDD, UDEL, UFORM kombinationen ikke findes
    i df2 (udd_udel_uform). 
    """
    
    # Definér unikke kombinationer af UDD, UDEL og UFORM i df2
    df2_pairs = df2.select(col1, col2, col3).distinct()

    # Left anti join beholder rækker fra df1 med ingen matches i df2
    missing = df1.join(df2_pairs, on=[col1, col2, col3], how="left_anti")

    return missing

def find_end_date_errors(df, audd_col="AUDD", end_col="afgtp"):
    """
    Returnerer rækker, hvor reglerne for slutdato er overtrådt:
      1. Hvis AUDD = 9999, skal afgtp være tom eller null.
      2. Hvis AUDD ikke er null og ikke 9999, skal afgtp være en gyldig dato (YYYY-MM-DD).
    """

    # --- Define "valid date" using regex for basic ISO date pattern ---
    valid_date_pattern = r"^\d{4}-\d{2}-\d{2}$"

    # --- Rule 1: AUDD = 9999 but end_date not null or non-empty ---
    rule1 = (F.col(audd_col) == 9999) & F.col(end_col).isNotNull() & (F.col(end_col) != "")

    # --- Rule 2: AUDD not null and not 9999, but end_date missing or invalid format ---
    rule2 = (
        (F.col(audd_col).isNotNull()) &
        (F.col(audd_col) != 9999) &
        (
            F.col(end_col).isNull() |
            (F.col(end_col) == "") |
            (~F.col(end_col).rlike(valid_date_pattern))
        )
    )

    # Combine both error conditions
    error_condition = rule1 | rule2

    # Filter rows that break the rules
    errors_df = df.filter(error_condition)

    return errors_df

def find_invalid_pnr_rows(df, id_col="pnr"):
    """
    Finder rækker hvor ID ikke overholder følgende regler:
    - De første 6 cifre danner en gyldig dato (format DDMMYY)
    - Det 7. og 10. tegn skal være et tal (0-9)

    Parametre:
        df (DataFrame): Spark DataFrame der indeholder kolonnen med ID.
        id_col (str): Navnet på ID-kolonnen.

    Returnerer:
        DataFrame: Rækker der ikke overholder betingelserne.
    """

    # 1. Check: Første 6 karakterer er digits og er en plausibel dato (format: DDMMYY)
    valid_date = F.col(id_col).substr(1, 6).rlike(
        "^(0[1-9]|[12][0-9]|3[01])(0[1-9]|1[0-2])[0-9]{2}$"
    )

    # 2. Check: 7. karakter er et digit
    # ER I TVIVL OM DENNE GÆLDER??
    #is_digit_7 = F.col(id_col).substr(7, 1).rlike("^[0-9]$")

    # 3. Check: 10. karakter er et digit
    is_digit_10 = F.col(id_col).substr(10, 1).rlike("^[0-9]$")

    # 4. Kombinér
    #valid_id = valid_date & is_digit_7 & is_digit_10
    valid_id = valid_date & is_digit_10

    # 5. Filter invalide rækker
    invalid_df = df.filter(~valid_id)

    return invalid_df

def missing_udd_audd_kombi(df1, df2, col1="UDD", col2="AUDD"):
    """
    Returns all rows from df1 where the (UDD, AUDD) combination
    is NOT found in df2. Assumes both DataFrames have the same column names.
    """
    # Filter til afgart_UDD6 == 2
    df1 = df1.filter(F.col("afgart_UDD6") == "2")
    
    # Select distinct name–surname pairs from df2
    df2_pairs = df2.select(col1, col2).distinct()

    # Left anti join keeps rows from df1 with no match in df2
    missing = df1.join(df2_pairs, on=[col1, col2], how="left_anti")

    return missing