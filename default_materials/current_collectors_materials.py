# %%
from steer_opencell_data.DataManager import DataManager
from steer_opencell_design import CurrentCollectorMaterial
from steer_opencell_design import __version__

from datetime import datetime as dt
import pandas as pd
# %%
import os
os.environ["OPENCELL_ENV"] = "development"
# %%
db = DataManager()
# %%
db.get_table_names()
# %%
db.drop_table('current_collector_materials')
# %%
db.create_table(table_name='current_collector_materials', columns={
    'name': 'TEXT',
    'object': 'TEXT',
    'date': 'TEXT',
    'version': 'TEXT'
})
# %%
# materials

aluminum = CurrentCollectorMaterial(
    name='Aluminum',
    density=2.70,
    specific_cost=2.9,
    color='#C0C0C0'
)

copper = CurrentCollectorMaterial(
    name='Copper',
    density=8.96,
    specific_cost=15.5,
    color='#B87333'
)

materials = [aluminum, copper]
pickled_materials = [m.serialize() for m in materials]
# %%
aluminum.specific_cost_range
# %%
# store data for current collectors

db.insert_data(table_name='current_collector_materials', data=pd.DataFrame({
    'name': [m.name for m in materials],
    'object': pickled_materials,
    'date': [m.last_updated for m in materials],
    'version': [__version__ for m in materials],
}))
# %%
db.get_current_collector_materials(most_recent=False)
# %%
db.get_current_collector_materials()
# %% [markdown]
