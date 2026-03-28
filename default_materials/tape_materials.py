# %%
from steer_opencell_data.DataManager import DataManager
from steer_opencell_design import TapeMaterial
from steer_materials import __version__
import pandas as pd
# %%
import os
os.environ["OPENCELL_ENV"] = "development"
# %%
db = DataManager()
# %%
db.get_table_names()
# %%
db.drop_table('tape_materials')
# %%
db.create_table(table_name='tape_materials', columns={
    'name': 'TEXT',
    'object': 'TEXT',
    'date': 'TEXT',
    'version': 'TEXT'
})
# %%
# materials

kapton = TapeMaterial(
    name="Kapton",
    density=1.42,
    specific_cost=70.0,
    color="#C9641F",
)

polyester = TapeMaterial(
    name="Polyester",
    density=1.38,
    specific_cost=8.0,
    color="#DCE2E8",
)
# %%
materials = [
    kapton,
    polyester,
]

pickled_materials = [m.serialize() for m in materials]
# %%
# store data for current collectors

db.insert_data(table_name='tape_materials', data=pd.DataFrame({
    'name': [m.name for m in materials],
    'object': pickled_materials,
    'date': [m.last_updated for m in materials],
    'version': [__version__ for m in materials],
}))
# %%
db.get_tape_materials(most_recent=False)
# %% [markdown]
