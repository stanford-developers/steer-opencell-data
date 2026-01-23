import sqlite3 as sql
from pathlib import Path
from typing import TypeVar, Optional, Union
import pandas as pd
import importlib.resources

from steer_core.Constants.Units import *
from steer_core.Mixins.Serializer import SerializerMixin


T = TypeVar('T', bound='SerializerMixin')


class DataManager:
    
    def __init__(self):
        # Get the database path and store it as a string
        with importlib.resources.path("steer_opencell_data", "database.db") as db_path:
            self._db_path = str(db_path)
        self._connection = sql.connect(self._db_path)
        self._cursor = self._connection.cursor()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def create_table(self, table_name: str, columns: dict):
        """
        Function to create a table in the database.

        :param table_name: Name of the table.
        :param columns: Dictionary of columns and their types.
        """
        columns_str = ", ".join([f"{k} {v}" for k, v in columns.items()])
        self._cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_str})")
        self._connection.commit()

    def drop_table(self, table_name: str):
        """
        Function to drop a table from the database.

        :param table_name: Name of the table.
        """
        self._cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        self._connection.commit()

    def get_table_names(self):
        """
        Function to get the names of all tables in the database.

        :return: List of table names.
        """
        self._cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        return [row[0] for row in self._cursor.fetchall()]

    def insert_data(self, table_name: str, data: pd.DataFrame) -> None:
        """
        Inserts data into the database only if it doesn't already exist.

        :param table_name: Name of the table.
        :param data: DataFrame containing the data to insert.
        """
        if data.empty:
            return
        
        columns = list(data.columns)
        placeholders = ", ".join(["?"] * len(columns))
        conditions = " AND ".join([f"{col} = ?" for col in columns])
        
        # Use INSERT OR IGNORE for better performance if you have UNIQUE constraints
        # Otherwise, check before inserting
        insert_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        check_query = f"SELECT COUNT(*) FROM {table_name} WHERE {conditions}"
        
        rows_to_insert = []
        for _, row in data.iterrows():
            row_tuple = tuple(row)
            self._cursor.execute(check_query, row_tuple)
            if self._cursor.fetchone()[0] == 0:
                rows_to_insert.append(row_tuple)
        
        # Batch insert
        if rows_to_insert:
            self._cursor.executemany(insert_query, rows_to_insert)
        
        self._connection.commit()

    def get_data(
        self,
        table_name: str,
        columns: Optional[list[str]] = None,
        condition: Optional[Union[str, list[str]]] = None,
        latest_column: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Retrieve data from the database.

        :param table_name: Name of the table.
        :param columns: List of columns to retrieve. If None, retrieves all columns.
        :param condition: Optional condition (single string or list of conditions).
        :param latest_column: Column name to find the most recent row.
        """
        # If columns is not provided, get all columns from the table
        if columns is None:
            self._cursor.execute(f"PRAGMA table_info({table_name})")
            columns_info = self._cursor.fetchall()
            columns = [col[1] for col in columns_info]  # Extract column names
            if not columns:
                raise ValueError(
                    f"Table '{table_name}' does not exist or has no columns."
                )

        columns_str = ", ".join(columns)
        query = f"SELECT {columns_str} FROM {table_name}"

        # Add condition if specified
        if condition:
            if isinstance(condition, list):
                condition_str = " AND ".join(condition)
            else:
                condition_str = condition
            query += f" WHERE {condition_str}"

        # If latest_column is provided, get the most recent entry
        if latest_column:
            query += f" ORDER BY {latest_column} DESC LIMIT 1"

        # Execute and return the result
        self._cursor.execute(query)
        data = self._cursor.fetchall()

        return pd.DataFrame(data, columns=columns)

    def get_unique_values(self, table_name: str, column_name: str) -> list:
        """
        Retrieves all unique values from a specified column.

        :param table_name: The name of the table.
        :param column_name: The column to retrieve unique values from.
        :return: A list of unique values.
        """
        query = f"SELECT DISTINCT {column_name} FROM {table_name}"
        self._cursor.execute(query)
        return [row[0] for row in self._cursor.fetchall()]
    
    def _get_materials(self, table_name: str, most_recent: bool = True) -> pd.DataFrame:
        """
        Generic method to retrieve materials from the database.

        :param table_name: The name of the table.
        :param most_recent: If True, returns only the most recent entry per name.
        :return: DataFrame with materials.
        """
        if most_recent:
            data = (
                self.get_data(table_name=table_name)
                .sort_values("date", ascending=False)
                .drop_duplicates(subset="name", keep="first")
                .reset_index(drop=True)
            )
        else:
            data = self.get_data(table_name=table_name)
        return data

    def get_current_collector_materials(self, most_recent: bool = True) -> pd.DataFrame:
        """
        Retrieves current collector materials from the database.

        :param most_recent: If True, returns only the most recent entry.
        :return: DataFrame with current collector materials.
        """
        return self._get_materials("current_collector_materials", most_recent)

    def get_insulation_materials(self, most_recent: bool = True) -> pd.DataFrame:
        """
        Retrieves insulation materials from the database.

        :param most_recent: If True, returns only the most recent entry.
        :return: DataFrame with insulation materials.
        """
        return self._get_materials("insulation_materials", most_recent)

    def get_cathode_materials(self, most_recent: bool = True) -> pd.DataFrame:
        """
        Retrieves cathode materials from the database.

        :param most_recent: If True, returns only the most recent entry.
        :return: DataFrame with cathode materials.
        """
        return self._get_materials("cathode_materials", most_recent)

    def get_anode_materials(self, most_recent: bool = True) -> pd.DataFrame:
        """
        Retrieves anode materials from the database.

        :param most_recent: If True, returns only the most recent entry.
        :return: DataFrame with anode materials.
        """
        return self._get_materials("anode_materials", most_recent)

    def get_binder_materials(self, most_recent: bool = True) -> pd.DataFrame:
        """
        Retrieves binder materials from the database.

        :param most_recent: If True, returns only the most recent entry.
        :return: DataFrame with binder materials.
        """
        return self._get_materials("binder_materials", most_recent)

    def get_conductive_additive_materials(
        self, most_recent: bool = True
    ) -> pd.DataFrame:
        """
        Retrieves conductive additives from the database.

        :param most_recent: If True, returns only the most recent entry.
        :return: DataFrame with conductive additives.
        """
        return self._get_materials("conductive_additive_materials", most_recent)

    def get_separator_materials(self, most_recent: bool = True) -> pd.DataFrame:
        """
        Retrieves separator materials from the database.

        :param most_recent: If True, returns only the most recent entry.
        :return: DataFrame with separator materials.
        """
        return self._get_materials("separator_materials", most_recent)
    
    def get_tape_materials(self, most_recent: bool = True) -> pd.DataFrame:
        """
        Retrieves tape materials from the database.

        :param most_recent: If True, returns only the most recent entry.
        :return: DataFrame with tape materials.
        """
        return self._get_materials("tape_materials", most_recent)

    def get_prismatic_container_materials(self, most_recent: bool = True) -> pd.DataFrame:
        """
        Retrieves prismatic container materials from the database.

        :param most_recent: If True, returns only the most recent entry.
        :return: DataFrame with prismatic container materials.
        """
        return self._get_materials("prismatic_container_materials", most_recent)

    @staticmethod
    def read_half_cell_curve(half_cell_path: Union[str, Path]) -> pd.DataFrame:
        """
        Function to read in a half cell curve for this active material

        :param half_cell_path: Path to the half cell data file.
        :return: DataFrame with the specific capacity and voltage.
        """
        try:
            data = pd.read_csv(half_cell_path)
        except FileNotFoundError:
            raise FileNotFoundError(f"Could not find the file at {half_cell_path}")
        except Exception as e:
            raise ValueError(f"Error reading file at {half_cell_path}: {str(e)}")

        if "Specific Capacity (mAh/g)" not in data.columns:
            raise ValueError(
                "The file must have a column named 'Specific Capacity (mAh/g)'"
            )

        if "Voltage (V)" not in data.columns:
            raise ValueError("The file must have a column named 'Voltage (V)'")

        if "Step_ID" not in data.columns:
            raise ValueError("The file must have a column named 'Step_ID'")

        data = (
            data.rename(
                columns={
                    "Specific Capacity (mAh/g)": "specific_capacity",
                    "Voltage (V)": "voltage",
                    "Step_ID": "step_id",
                }
            )
            .assign(
                specific_capacity=lambda x: x["specific_capacity"]
                * (H_TO_S * mA_TO_A / G_TO_KG)
            )
            .filter(["specific_capacity", "voltage", "step_id"])
            .groupby(["specific_capacity", "step_id"], group_keys=False)["voltage"]
            .max()
            .reset_index()
            .sort_values(["step_id", "specific_capacity"])
        )

        return data

    def remove_data(self, table_name: str, condition: str):
        """
        Function to remove data from the database.

        :param table_name: Name of the table.
        :param condition: Condition to remove rows.
        """
        self._cursor.execute(f"DELETE FROM {table_name} WHERE {condition}")
        self._connection.commit()

    def close(self) -> None:
        """Explicitly close the database connection."""
        if hasattr(self, '_connection') and self._connection:
            self._connection.commit()
            self._connection.close()
    
    def __del__(self):
        """Fallback cleanup - prefer using context manager or calling close() explicitly."""
        self.close()


